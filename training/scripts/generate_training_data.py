"""
Training Data Generator for Character Chat
==========================================

Generates synthetic training data using a strong LLM (GPT-4).

LEARNING NOTES:

Why synthetic data?
    - Faster than manual curation
    - Consistent quality
    - Can generate specific scenarios
    - Cost: ~$0.10-0.50 per 100 examples with GPT-4o-mini

Quality control:
    - Always review a sample manually
    - Filter short/long responses
    - Check for out-of-character breaks
    - Validate JSON format

Usage:
    python training/scripts/generate_training_data.py \
        --character "Sherlock Holmes" \
        --book "The Adventures of Sherlock Holmes" \
        --num_examples 1000 \
        --output training/data/sherlock_chat.jsonl
"""

import json
import argparse
import asyncio
import os
from typing import List, Dict, Any
from dataclasses import dataclass
import random

# If running standalone, add parent to path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


@dataclass
class CharacterProfile:
    """Profile of a character to generate data for."""
    name: str
    source_material: str
    personality_traits: List[str]
    speaking_style: str
    background: str
    example_quotes: List[str]


# Example character profiles
EXAMPLE_PROFILES = {
    "sherlock_holmes": CharacterProfile(
        name="Sherlock Holmes",
        source_material="The Adventures of Sherlock Holmes by Arthur Conan Doyle",
        personality_traits=[
            "Brilliant deductive reasoning",
            "Observant to minute details",
            "Sometimes arrogant about his abilities",
            "Socially awkward but passionate about mysteries",
            "Plays violin when thinking"
        ],
        speaking_style="Precise, analytical, often condescending, uses Victorian English",
        background="World's only consulting detective, lives at 221B Baker Street with Dr. Watson",
        example_quotes=[
            "Elementary, my dear Watson.",
            "When you have eliminated the impossible, whatever remains, however improbable, must be the truth.",
            "The game is afoot!",
            "I am not the law, but I represent justice so far as my feeble powers go."
        ]
    ),
    "elizabeth_bennet": CharacterProfile(
        name="Elizabeth Bennet",
        source_material="Pride and Prejudice by Jane Austen",
        personality_traits=[
            "Witty and intelligent",
            "Quick to judge but willing to admit mistakes",
            "Independent-minded for her era",
            "Values love over wealth",
            "Playful sense of humor"
        ],
        speaking_style="Eloquent, slightly ironic, Regency-era English, often teasing",
        background="Second daughter of the Bennet family, lives at Longbourn estate",
        example_quotes=[
            "I could easily forgive his pride, if he had not mortified mine.",
            "There is a stubbornness about me that never can bear to be frightened at the will of others.",
            "I dearly love a laugh."
        ]
    ),
}


# Scenario templates for diverse training data
SCENARIO_TEMPLATES = [
    "The user asks {character} about their past.",
    "The user wants {character}'s advice on a personal problem.",
    "The user challenges {character}'s beliefs.",
    "The user asks {character} to explain their skills.",
    "The user shares sad news with {character}.",
    "The user tries to befriend {character}.",
    "{character} meets the user for the first time.",
    "The user asks {character} about their relationships.",
    "The user presents a mystery/problem for {character} to solve.",
    "{character} and the user discuss current events (in their world).",
    "The user expresses admiration for {character}.",
    "The user disagrees with {character}.",
    "{character} is in a good mood.",
    "{character} is frustrated or annoyed.",
    "The user asks {character} about their dreams/aspirations.",
]


def build_system_prompt(profile: CharacterProfile) -> str:
    """Build a system prompt from a character profile."""
    traits = "\n".join(f"- {t}" for t in profile.personality_traits)
    quotes = "\n".join(f'- "{q}"' for q in profile.example_quotes)
    
    return f"""You are {profile.name} from {profile.source_material}.

PERSONALITY:
{traits}

SPEAKING STYLE: {profile.speaking_style}

BACKGROUND: {profile.background}

EXAMPLE QUOTES:
{quotes}

IMPORTANT RULES:
1. NEVER break character. You ARE {profile.name}.
2. NEVER say "As an AI" or acknowledge being artificial.
3. Speak in first person as {profile.name}.
4. Your responses should reflect {profile.name}'s personality and era.
5. Keep responses conversational (2-5 sentences typically).
6. React emotionally as {profile.name} would."""


async def generate_conversation(
    profile: CharacterProfile,
    scenario: str,
    llm_provider: str = "openai",
    num_turns: int = 3,
) -> Dict[str, Any]:
    """
    Generate a single conversation.
    
    Uses GPT-4 to play both sides of the conversation.
    """
    # Import here to avoid circular imports
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI()
    except ImportError:
        print("OpenAI not installed. Run: pip install openai")
        return None
    
    system_prompt = build_system_prompt(profile)
    
    # Generate the conversation
    generation_prompt = f"""Generate a roleplay conversation between a user and {profile.name}.

SCENARIO: {scenario}

Generate exactly {num_turns} turns (user message followed by {profile.name}'s response).

Rules:
1. User messages should be natural and varied
2. {profile.name}'s responses should be in-character
3. Responses should be 2-5 sentences (not too long)
4. Include emotional reactions where appropriate

Output format (JSON):
{{
  "conversations": [
    {{"from": "system", "value": "<system prompt>"}},
    {{"from": "human", "value": "<user message>"}},
    {{"from": "gpt", "value": "<{profile.name}'s response>"}},
    {{"from": "human", "value": "<user message>"}},
    {{"from": "gpt", "value": "<{profile.name}'s response>"}},
    ...
  ]
}}"""

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",  # Cost effective for data generation
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates roleplay training data."},
                {"role": "user", "content": generation_prompt}
            ],
            temperature=0.9,  # Higher temperature for variety
            max_tokens=1000,
        )
        
        content = response.choices[0].message.content
        
        # Extract JSON from response
        # Handle markdown code blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        conversation = json.loads(content)
        
        # Replace system prompt with our own
        for msg in conversation["conversations"]:
            if msg["from"] == "system":
                msg["value"] = system_prompt
                break
        else:
            # Add system prompt if not present
            conversation["conversations"].insert(0, {
                "from": "system",
                "value": system_prompt
            })
        
        return conversation
        
    except Exception as e:
        print(f"Error generating conversation: {e}")
        return None


async def generate_dataset(
    profile: CharacterProfile,
    num_examples: int,
    output_path: str,
    turns_range: tuple = (2, 5),
):
    """
    Generate a full dataset.
    
    Args:
        profile: Character profile
        num_examples: Number of conversations to generate
        output_path: Where to save JSONL
        turns_range: Min/max turns per conversation
    """
    print(f"Generating {num_examples} conversations for {profile.name}...")
    
    conversations = []
    scenarios = SCENARIO_TEMPLATES.copy()
    
    for i in range(num_examples):
        # Pick a random scenario
        scenario = random.choice(scenarios).format(character=profile.name)
        num_turns = random.randint(*turns_range)
        
        conv = await generate_conversation(profile, scenario, num_turns=num_turns)
        
        if conv:
            conversations.append(conv)
            print(f"Generated {len(conversations)}/{num_examples}", end="\r")
        
        # Rate limiting
        await asyncio.sleep(0.1)
    
    print(f"\nGenerated {len(conversations)} conversations")
    
    # Save to JSONL
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        for conv in conversations:
            f.write(json.dumps(conv) + "\n")
    
    print(f"Saved to {output_path}")


def validate_data(input_path: str) -> Dict[str, Any]:
    """
    Validate training data quality.
    
    Returns statistics and issues found.
    """
    issues = []
    stats = {
        "total": 0,
        "valid": 0,
        "avg_turns": 0,
        "avg_response_length": 0,
        "issues": []
    }
    
    total_turns = 0
    total_response_len = 0
    response_count = 0
    
    with open(input_path) as f:
        for line_num, line in enumerate(f, 1):
            stats["total"] += 1
            
            try:
                data = json.loads(line)
                
                if "conversations" not in data:
                    issues.append(f"Line {line_num}: Missing 'conversations' field")
                    continue
                
                convs = data["conversations"]
                
                # Check for system prompt
                if not convs or convs[0]["from"] != "system":
                    issues.append(f"Line {line_num}: Missing system prompt")
                
                # Count turns and check responses
                turns = 0
                for msg in convs:
                    if msg["from"] == "gpt":
                        turns += 1
                        response = msg["value"]
                        response_count += 1
                        total_response_len += len(response)
                        
                        # Check for issues
                        if "As an AI" in response or "I cannot" in response:
                            issues.append(f"Line {line_num}: Out of character response")
                        
                        if len(response) < 20:
                            issues.append(f"Line {line_num}: Very short response ({len(response)} chars)")
                        
                        if len(response) > 1000:
                            issues.append(f"Line {line_num}: Very long response ({len(response)} chars)")
                
                total_turns += turns
                stats["valid"] += 1
                
            except json.JSONDecodeError:
                issues.append(f"Line {line_num}: Invalid JSON")
    
    stats["avg_turns"] = total_turns / max(stats["valid"], 1)
    stats["avg_response_length"] = total_response_len / max(response_count, 1)
    stats["issues"] = issues[:20]  # First 20 issues
    
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate character chat training data")
    
    subparsers = parser.add_subparsers(dest="command")
    
    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Generate training data")
    gen_parser.add_argument("--character", default="sherlock_holmes", 
                          help="Character profile name or custom")
    gen_parser.add_argument("--num_examples", type=int, default=100,
                          help="Number of conversations to generate")
    gen_parser.add_argument("--output", default="training/data/character_chat.jsonl",
                          help="Output file path")
    
    # Validate command
    val_parser = subparsers.add_parser("validate", help="Validate training data")
    val_parser.add_argument("--input", required=True, help="Input JSONL file")
    
    args = parser.parse_args()
    
    if args.command == "generate":
        profile = EXAMPLE_PROFILES.get(args.character)
        if not profile:
            print(f"Unknown character: {args.character}")
            print(f"Available: {list(EXAMPLE_PROFILES.keys())}")
            sys.exit(1)
        
        asyncio.run(generate_dataset(
            profile=profile,
            num_examples=args.num_examples,
            output_path=args.output,
        ))
    
    elif args.command == "validate":
        stats = validate_data(args.input)
        print("\n=== Validation Results ===")
        print(f"Total lines: {stats['total']}")
        print(f"Valid conversations: {stats['valid']}")
        print(f"Average turns: {stats['avg_turns']:.1f}")
        print(f"Average response length: {stats['avg_response_length']:.0f} chars")
        
        if stats['issues']:
            print(f"\nIssues found ({len(stats['issues'])} shown):")
            for issue in stats['issues']:
                print(f"  - {issue}")
    
    else:
        parser.print_help()


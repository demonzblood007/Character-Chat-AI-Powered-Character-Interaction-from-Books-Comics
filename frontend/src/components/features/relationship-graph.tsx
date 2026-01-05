"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import dynamic from "next/dynamic";
import Image from "next/image";
import Link from "next/link";
import { 
  X, 
  MessageCircle, 
  Heart, 
  Swords, 
  Users, 
  HelpCircle,
  Maximize2,
  Minimize2,
  ZoomIn,
  ZoomOut,
  RotateCcw
} from "lucide-react";

// Dynamic import for force graph (SSR issues)
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center">
      <div className="w-12 h-12 rounded-full border-2 border-accent-primary border-t-transparent animate-spin" />
    </div>
  ),
});

// Relationship types with colors and icons
const RELATIONSHIP_TYPES = {
  romantic: { 
    color: "#fb7185", 
    label: "Romantic",
    icon: Heart,
    gradient: "from-rose-500 to-pink-600"
  },
  family: { 
    color: "#fbbf24", 
    label: "Family",
    icon: Users,
    gradient: "from-amber-500 to-orange-600"
  },
  friend: { 
    color: "#34d399", 
    label: "Friend",
    icon: Users,
    gradient: "from-emerald-500 to-teal-600"
  },
  rival: { 
    color: "#f87171", 
    label: "Rival",
    icon: Swords,
    gradient: "from-red-500 to-orange-600"
  },
  mentor: { 
    color: "#a78bfa", 
    label: "Mentor",
    icon: Users,
    gradient: "from-violet-500 to-purple-600"
  },
  unknown: { 
    color: "#71717a", 
    label: "Unknown",
    icon: HelpCircle,
    gradient: "from-zinc-500 to-zinc-600"
  },
};

interface Character {
  id: string;
  name: string;
  avatar?: string;
  description?: string;
}

interface Relationship {
  source: string;
  target: string;
  type: keyof typeof RELATIONSHIP_TYPES;
  description?: string;
}

interface RelationshipGraphProps {
  characters: Character[];
  relationships: Relationship[];
  bookTitle?: string;
  onCharacterClick?: (character: Character) => void;
}

export function RelationshipGraph({
  characters,
  relationships,
  bookTitle = "Book",
  onCharacterClick,
}: RelationshipGraphProps) {
  const graphRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [selectedNode, setSelectedNode] = useState<Character | null>(null);
  const [hoveredNode, setHoveredNode] = useState<Character | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  // Update dimensions on resize
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        setDimensions({
          width: rect.width || 800,
          height: isFullscreen ? window.innerHeight - 100 : Math.min(rect.height, 600),
        });
      }
    };

    updateDimensions();
    window.addEventListener("resize", updateDimensions);
    return () => window.removeEventListener("resize", updateDimensions);
  }, [isFullscreen]);

  // Prepare graph data
  const graphData = {
    nodes: characters.map((char) => ({
      id: char.id,
      name: char.name,
      avatar: char.avatar,
      description: char.description,
      val: relationships.filter(
        (r) => r.source === char.id || r.target === char.id
      ).length + 1, // Size based on connections
    })),
    links: relationships.map((rel) => ({
      source: rel.source,
      target: rel.target,
      type: rel.type,
      description: rel.description,
      color: RELATIONSHIP_TYPES[rel.type]?.color || RELATIONSHIP_TYPES.unknown.color,
    })),
  };

  // Custom node rendering
  const nodeCanvasObject = useCallback(
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      // Guard against undefined coordinates
      if (typeof node.x !== 'number' || typeof node.y !== 'number' || !isFinite(node.x) || !isFinite(node.y)) {
        return;
      }

      const isSelected = selectedNode?.id === node.id;
      const isHovered = hoveredNode?.id === node.id;
      const size = Math.max(8, Math.min(20, (node.val || 1) * 3));
      // Keep labels readable but never explode when zoomed out (globalScale < 1)
      const fontSize = Math.max(9, Math.min(14, 12 / Math.max(1, globalScale)));

      // Glow effect for selected/hovered
      if (isSelected || isHovered) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, size + 8, 0, 2 * Math.PI);
        ctx.fillStyle = isSelected ? "rgba(167, 139, 250, 0.3)" : "rgba(167, 139, 250, 0.15)";
        ctx.fill();
      }

      // Node circle with solid gradient-like colors
      ctx.beginPath();
      ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
      ctx.fillStyle = "#8b5cf6";
      ctx.fill();

      // Border
      ctx.strokeStyle = isSelected ? "#fbbf24" : "#a78bfa";
      ctx.lineWidth = isSelected ? 3 : 1.5;
      ctx.stroke();

      // Name label
      ctx.font = `${isSelected ? "bold " : ""}${fontSize}px "DM Sans", sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      
      // Text background
      const textWidth = ctx.measureText(node.name || "").width;
      ctx.fillStyle = "rgba(5, 5, 8, 0.8)";
      ctx.fillRect(
        node.x - textWidth / 2 - 4,
        node.y + size + 4,
        textWidth + 8,
        fontSize + 6
      );
      
      // Text
      ctx.fillStyle = isSelected ? "#fbbf24" : "#fafafa";
      ctx.fillText(node.name || "", node.x, node.y + size + 6);
    },
    [selectedNode, hoveredNode]
  );

  // Custom link rendering
  const linkCanvasObject = useCallback(
    (link: any, ctx: CanvasRenderingContext2D) => {
      const start = link.source;
      const end = link.target;

      if (typeof start !== "object" || typeof end !== "object") return;

      // Draw link
      ctx.beginPath();
      ctx.moveTo(start.x, start.y);
      ctx.lineTo(end.x, end.y);
      ctx.strokeStyle = link.color || "#71717a";
      ctx.lineWidth = 2;
      ctx.globalAlpha = 0.6;
      ctx.stroke();
      ctx.globalAlpha = 1;
    },
    []
  );

  const handleNodeClick = useCallback(
    (node: any) => {
      const character = characters.find((c) => c.id === node.id);
      if (character) {
        setSelectedNode(character);
        onCharacterClick?.(character);
      }
    },
    [characters, onCharacterClick]
  );

  const handleNodeHover = useCallback(
    (node: any) => {
      const character = node ? characters.find((c) => c.id === node.id) : null;
      setHoveredNode(character || null);
    },
    [characters]
  );

  const handleZoomIn = () => {
    graphRef.current?.zoom(graphRef.current.zoom() * 1.3, 400);
  };

  const handleZoomOut = () => {
    graphRef.current?.zoom(graphRef.current.zoom() / 1.3, 400);
  };

  const handleReset = () => {
    graphRef.current?.zoomToFit(400, 50);
    setSelectedNode(null);
  };

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  return (
    <div
      ref={containerRef}
      className={`relative rounded-2xl overflow-hidden border border-border bg-bg-secondary ${
        isFullscreen ? "fixed inset-4 z-50" : "w-full h-[600px]"
      }`}
    >
      {/* Background pattern */}
      <div className="absolute inset-0 opacity-30">
        <svg width="100%" height="100%">
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path
                d="M 40 0 L 0 0 0 40"
                fill="none"
                stroke="rgba(167, 139, 250, 0.1)"
                strokeWidth="1"
              />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
        </svg>
      </div>

      {/* Header */}
      <div className="absolute top-0 left-0 right-0 z-10 p-4 flex items-center justify-between glass">
        <div>
          <h3 className="font-display text-lg font-medium text-text-primary">
            Character Relationships
          </h3>
          <p className="text-sm text-text-muted">{bookTitle}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleZoomIn}
            className="p-2 rounded-lg hover:bg-bg-tertiary text-text-muted hover:text-text-primary transition-all"
          >
            <ZoomIn className="w-5 h-5" />
          </button>
          <button
            onClick={handleZoomOut}
            className="p-2 rounded-lg hover:bg-bg-tertiary text-text-muted hover:text-text-primary transition-all"
          >
            <ZoomOut className="w-5 h-5" />
          </button>
          <button
            onClick={handleReset}
            className="p-2 rounded-lg hover:bg-bg-tertiary text-text-muted hover:text-text-primary transition-all"
          >
            <RotateCcw className="w-5 h-5" />
          </button>
          <button
            onClick={toggleFullscreen}
            className="p-2 rounded-lg hover:bg-bg-tertiary text-text-muted hover:text-text-primary transition-all"
          >
            {isFullscreen ? (
              <Minimize2 className="w-5 h-5" />
            ) : (
              <Maximize2 className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>

      {/* Graph */}
      <ForceGraph2D
        ref={graphRef}
        graphData={graphData}
        width={dimensions.width}
        height={dimensions.height}
        nodeCanvasObject={nodeCanvasObject}
        linkCanvasObject={linkCanvasObject}
        onNodeClick={handleNodeClick}
        onNodeHover={handleNodeHover}
        nodeRelSize={6}
        linkWidth={2}
        linkDirectionalParticles={2}
        linkDirectionalParticleWidth={2}
        linkDirectionalParticleSpeed={0.005}
        backgroundColor="transparent"
        cooldownTicks={100}
        onEngineStop={() => graphRef.current?.zoomToFit(400, 50)}
        enableZoomInteraction={true}
        enablePanInteraction={true}
      />

      {/* Legend */}
      <div className="absolute bottom-4 left-4 glass rounded-xl p-4">
        <p className="text-xs text-text-muted uppercase tracking-wider mb-3">Relationships</p>
        <div className="grid grid-cols-2 gap-2">
          {Object.entries(RELATIONSHIP_TYPES).slice(0, -1).map(([key, value]) => (
            <div key={key} className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: value.color }}
              />
              <span className="text-xs text-text-secondary">{value.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Selected Character Panel */}
      <AnimatePresence>
        {selectedNode && (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            className="absolute top-20 right-4 w-72 glass-strong rounded-2xl overflow-hidden"
          >
            <div className="p-4">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="avatar-ring p-0.5">
                    <Image
                      src={selectedNode.avatar || `https://api.dicebear.com/7.x/avataaars/svg?seed=${encodeURIComponent(selectedNode.name)}`}
                      alt={selectedNode.name}
                      width={48}
                      height={48}
                      className="rounded-full"
                    />
                  </div>
                  <div>
                    <h4 className="font-display font-medium text-text-primary">
                      {selectedNode.name}
                    </h4>
                    <p className="text-xs text-accent-primary">
                      {relationships.filter(
                        (r) => r.source === selectedNode.id || r.target === selectedNode.id
                      ).length} connections
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setSelectedNode(null)}
                  className="p-1.5 rounded-lg hover:bg-bg-tertiary text-text-muted"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {selectedNode.description && (
                <p className="text-sm text-text-secondary mb-4 line-clamp-3">
                  {selectedNode.description}
                </p>
              )}

              {/* Character's relationships */}
              <div className="space-y-2 mb-4">
                <p className="text-xs text-text-muted uppercase tracking-wider">Connections</p>
                {relationships
                  .filter((r) => r.source === selectedNode.id || r.target === selectedNode.id)
                  .slice(0, 4)
                  .map((rel, i) => {
                    const otherId = rel.source === selectedNode.id ? rel.target : rel.source;
                    const other = characters.find((c) => c.id === otherId);
                    const type = RELATIONSHIP_TYPES[rel.type] || RELATIONSHIP_TYPES.unknown;
                    const TypeIcon = type.icon;
                    
                    return (
                      <div
                        key={i}
                        className="flex items-center gap-2 text-sm"
                      >
                        <div
                          className="w-6 h-6 rounded-full flex items-center justify-center"
                          style={{ backgroundColor: `${type.color}20` }}
                        >
                          <TypeIcon className="w-3 h-3" style={{ color: type.color }} />
                        </div>
                        <span className="text-text-secondary">{other?.name}</span>
                        <span className="text-text-muted text-xs">({type.label})</span>
                      </div>
                    );
                  })}
              </div>

              <Link href={`/chat/${encodeURIComponent(selectedNode.name)}`}>
                <button className="btn-magic w-full text-sm py-2.5 flex items-center justify-center gap-2">
                  <MessageCircle className="w-4 h-4" />
                  Chat with {selectedNode.name}
                </button>
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Instructions tooltip */}
      {!selectedNode && (
        <div className="absolute bottom-4 right-4 text-xs text-text-muted glass rounded-lg px-3 py-2">
          Click a character to see details • Drag to pan • Scroll to zoom
        </div>
      )}
    </div>
  );
}

export default RelationshipGraph;


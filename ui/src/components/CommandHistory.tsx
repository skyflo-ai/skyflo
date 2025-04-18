"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { FaStar, FaRegStar, FaHistory, FaTrash, FaPlay } from "react-icons/fa";
import { RxCopy } from "react-icons/rx";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export interface Command {
  id: string;
  text: string;
  timestamp: number;
  isFavorite: boolean;
  result?: string;
}

interface CommandHistoryProps {
  commands: Command[];
  onCommandSelect: (command: string) => void;
  onToggleFavorite: (id: string) => void;
  onDeleteCommand: (id: string) => void;
}

export function CommandHistory({
  commands,
  onCommandSelect,
  onToggleFavorite,
  onDeleteCommand,
}: CommandHistoryProps) {
  const [filter, setFilter] = useState<"all" | "favorites">("all");
  const [searchTerm, setSearchTerm] = useState("");

  const filteredCommands = commands
    .filter((command) => {
      if (filter === "favorites") {
        return command.isFavorite;
      }
      return true;
    })
    .filter((command) => {
      if (searchTerm.trim() === "") return true;
      return command.text.toLowerCase().includes(searchTerm.toLowerCase());
    });

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const formatDate = (timestamp: number) => {
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  return (
    <Card className="bg-gradient-to-br from-gray-900/95 to-gray-800/95 border border-gray-800/50 shadow-xl">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-md font-bold text-gray-200 flex items-center gap-2">
          <FaHistory className="w-4 h-4 text-blue-400" />
          Command History
        </CardTitle>
        <div className="flex items-center gap-2">
          <Button
            variant={filter === "all" ? "default" : "outline"}
            size="sm"
            onClick={() => setFilter("all")}
            className="h-8 px-2 text-xs"
          >
            All
          </Button>
          <Button
            variant={filter === "favorites" ? "default" : "outline"}
            size="sm"
            onClick={() => setFilter("favorites")}
            className="h-8 px-2 text-xs"
          >
            Favorites
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="relative mb-4">
          <input
            type="text"
            placeholder="Search commands..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-md text-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {filteredCommands.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-gray-500 text-sm">
            <FaHistory className="w-8 h-8 mb-3 opacity-30" />
            <p>No commands in history</p>
          </div>
        ) : (
          <div className="space-y-3 max-h-96 overflow-y-auto">
            <AnimatePresence>
              {filteredCommands.map((command) => (
                <motion.div
                  key={command.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="bg-gray-800/50 rounded-lg border border-gray-700/50 overflow-hidden"
                >
                  <div className="p-3">
                    <div className="flex justify-between items-start">
                      <p className="text-sm text-gray-300 mb-1 line-clamp-2">
                        {command.text}
                      </p>
                      <div className="flex items-center gap-1 ml-2">
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <button
                              onClick={() => onToggleFavorite(command.id)}
                              className="text-gray-400 hover:text-yellow-400 transition-colors p-1"
                            >
                              {command.isFavorite ? (
                                <FaStar className="w-3.5 h-3.5 text-yellow-400" />
                              ) : (
                                <FaRegStar className="w-3.5 h-3.5" />
                              )}
                            </button>
                          </TooltipTrigger>
                          <TooltipContent side="left">
                            {command.isFavorite
                              ? "Remove from favorites"
                              : "Add to favorites"}
                          </TooltipContent>
                        </Tooltip>
                      </div>
                    </div>
                    <div className="flex items-center justify-between mt-2">
                      <p className="text-xs text-gray-500">
                        {formatDate(command.timestamp)}
                      </p>
                      <div className="flex items-center gap-1">
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <button
                              onClick={() => onCommandSelect(command.text)}
                              className="text-gray-400 hover:text-blue-400 transition-colors p-1"
                            >
                              <FaPlay className="w-3 h-3" />
                            </button>
                          </TooltipTrigger>
                          <TooltipContent side="left">
                            Run command
                          </TooltipContent>
                        </Tooltip>

                        <Tooltip>
                          <TooltipTrigger asChild>
                            <button
                              onClick={() => copyToClipboard(command.text)}
                              className="text-gray-400 hover:text-blue-400 transition-colors p-1"
                            >
                              <RxCopy className="w-3.5 h-3.5" />
                            </button>
                          </TooltipTrigger>
                          <TooltipContent side="left">
                            Copy to clipboard
                          </TooltipContent>
                        </Tooltip>

                        <Tooltip>
                          <TooltipTrigger asChild>
                            <button
                              onClick={() => onDeleteCommand(command.id)}
                              className="text-gray-400 hover:text-red-400 transition-colors p-1"
                            >
                              <FaTrash className="w-3 h-3" />
                            </button>
                          </TooltipTrigger>
                          <TooltipContent side="left">
                            Delete command
                          </TooltipContent>
                        </Tooltip>
                      </div>
                    </div>
                  </div>
                  {command.result && (
                    <div className="text-xs bg-gray-900/60 border-t border-gray-700/50 p-2 text-gray-400 max-h-24 overflow-y-auto">
                      <p className="font-mono whitespace-pre-wrap">
                        {command.result}
                      </p>
                    </div>
                  )}
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

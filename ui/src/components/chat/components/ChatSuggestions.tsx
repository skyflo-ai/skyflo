import { motion } from "framer-motion";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { HiArrowRight } from "react-icons/hi2";

import { ChatSuggestionsProps, Suggestion } from "../types";

const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: (index: number) => ({
    opacity: 1,
    y: 0,
    transition: {
      delay: index * 0.1,
      duration: 0.4,
      type: "spring",
      stiffness: 100,
      damping: 20,
    },
  }),
  hover: {
    y: -6,
    boxShadow: "0 10px 25px -5px rgba(59, 130, 246, 0.15)",
    borderColor: "rgba(59, 130, 246, 0.4)",
    transition: {
      duration: 0.3,
    },
  },
};

const ChatSuggestions = ({
  suggestions,
  onSuggestionClick,
}: ChatSuggestionsProps) => {
  return (
    <div className="flex flex-wrap items-center justify-center gap-6 w-full mx-auto relative mt-8">
      {suggestions.map((suggestion, index) => (
        <motion.div
          key={index}
          initial="hidden"
          animate="visible"
          whileHover="hover"
          variants={cardVariants}
          custom={index}
          className="cursor-pointer group w-full sm:w-[500px] max-w-full"
          onClick={() => onSuggestionClick(suggestion.text)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              onSuggestionClick(suggestion.text);
            }
          }}
          tabIndex={0}
          role="button"
          aria-label={`Select suggestion: ${suggestion.text}`}
        >
          <Card className="bg-gradient-to-br from-[#0A1525] to-[#142338] border border-[#1E2D45] rounded-xl overflow-hidden transition-all duration-300 h-[140px] shadow-lg shadow-black/5">
            <CardHeader className="p-5">
              <div className="flex items-start space-x-5">
                <div className="bg-gradient-to-br from-blue-800/10 to-blue-700/10 p-3 rounded-xl shadow-lg shadow-blue-900/5 backdrop-blur-sm transform group-hover:scale-110 transition-transform duration-300">
                  <span className="text-blue-400 group-hover:text-blue-300 transition-colors">
                    <suggestion.icon className="w-4 h-4" />
                  </span>
                </div>
                <div className="space-y-2 flex-1 mt-1">
                  <CardTitle className="text-sm font-semibold text-blue-400/80 h-6 group-hover:text-blue-300/90 transition-colors">
                    {suggestion.category}
                  </CardTitle>
                  <CardDescription className="text-slate-200 text-base font-medium tracking-tight group-hover:text-slate-100 transition-colors">
                    {suggestion.text}
                  </CardDescription>
                </div>
                <motion.div
                  className="flex items-center justify-center bg-blue-500/10 rounded-full p-1.5 opacity-0 group-hover:opacity-100 transition-opacity"
                  initial={{ x: -5 }}
                  whileHover={{ scale: 1.2, x: 0 }}
                >
                  <HiArrowRight className="w-3 h-3 text-blue-400" />
                </motion.div>
              </div>
            </CardHeader>
          </Card>
        </motion.div>
      ))}
    </div>
  );
};

export default ChatSuggestions;

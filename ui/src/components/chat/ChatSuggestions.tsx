import { motion } from "framer-motion";
import { MdSearch, MdElectricBolt, MdRefresh, MdDelete } from "react-icons/md";

const INITIAL_SUGGESTIONS = [
  {
    text: "Get all pods in the ... namespace",
    icon: MdSearch,
    category: "Query",
  },
  {
    text: "Create a new deployment in the ... namespace",
    icon: MdElectricBolt,
    category: "Create Deployment",
  },
  {
    text: "Restart all deployments in the ... namespace",
    icon: MdRefresh,
    category: "Restart Deployment",
  },
  {
    text: "Delete the ... service in the ... namespace",
    icon: MdDelete,
    category: "Delete Resource",
  },
];

export interface ChatSuggestionsProps {
  onSuggestionClick: (suggestion: string) => void;
}

const cardVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: (index: number) => ({
    opacity: 1,
    y: 0,
    transition: {
      delay: index * 0.05,
      duration: 0.3,
      type: "spring",
      stiffness: 120,
      damping: 25,
    },
  }),
};

const ChatSuggestions = ({ onSuggestionClick }: ChatSuggestionsProps) => {
  return (
    <div className="flex flex-wrap items-center justify-center gap-3 w-full mx-auto">
      {INITIAL_SUGGESTIONS.map((suggestion, index) => (
        <motion.button
          key={index}
          initial="hidden"
          animate="visible"
          whileHover="hover"
          variants={cardVariants}
          custom={index}
          className="group inline-flex items-center gap-2 px-4 py-2.5 rounded-lg
                   bg-[#0A1525]/50 border border-blue-500/30 
                   hover:border-blue-500/40 hover:bg-[#0A1525]/80
                   outline-none focus:outline-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 focus-visible:ring-offset-0
                   transition-all duration-100 cursor-pointer"
          onClick={() => onSuggestionClick(suggestion.text)}
          aria-label={`Select suggestion: ${suggestion.text}`}
        >
          <span className="text-blue-400/70 group-hover:text-blue-400 transition-colors">
            <suggestion.icon className="w-3.5 h-3.5" />
          </span>
          <span className="text-slate-300 text-sm font-medium">
            {suggestion.text}
          </span>
        </motion.button>
      ))}
    </div>
  );
};

export default ChatSuggestions;

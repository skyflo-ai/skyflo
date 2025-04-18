import { RxReload } from "react-icons/rx";
import { MdStop, MdRefresh } from "react-icons/md";
import { motion } from "framer-motion";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
  TooltipProvider,
} from "@/components/ui/tooltip";
import Image from "next/image";
interface ChatInputProps {
  inputValue: string;
  setInputValue: (value: string) => void;
  handleSubmit: (e?: React.FormEvent) => void;
  handleReloadChat: () => void;
  isAgentResponding: boolean;
  showReloadButton?: boolean;
  messagesExist?: boolean;
  handleRestartConnection?: () => void;
  handleCancelResponse?: () => void;
}

const ChatInput = ({
  inputValue,
  setInputValue,
  handleSubmit,
  handleReloadChat,
  isAgentResponding,
  showReloadButton = true,
  messagesExist = false,
  handleRestartConnection,
  handleCancelResponse,
}: ChatInputProps) => {
  return (
    <div className="pb-4 px-4 w-full">
      <form onSubmit={handleSubmit} className="relative w-full">
        <div className="w-full relative">
          <motion.div
            initial={{ y: 10, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.3 }}
            className="relative"
          >
            <textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              autoFocus
              placeholder={
                isAgentResponding
                  ? "Please wait while Sky is responding. Click reload to start over."
                  : "Ask Sky to perform any action on your Kubernetes setup."
              }
              className="w-full p-4 bg-[#0A1628] text-white text-sm tracking-wide 
                border border-[#1A2B44] rounded-xl
                focus:outline-none focus:ring-1 focus:ring-blue-500/30 focus:border-blue-500/50
                resize-none h-auto min-h-[100px] overflow-hidden
                transition-all duration-200
                placeholder:text-[#4B5563]"
              rows={1}
              onInput={(e: React.FormEvent<HTMLTextAreaElement>) => {
                const target = e.target as HTMLTextAreaElement;
                target.style.height = "auto";
                target.style.height = `${target.scrollHeight}px`;
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && e.metaKey) {
                  handleSubmit(e);
                }
              }}
              disabled={isAgentResponding}
            />

            {messagesExist && showReloadButton ? (
              <div className="">
                <div className="absolute left-4 bottom-4 flex items-start space-x-3">
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <motion.button
                          type="button"
                          onClick={handleReloadChat}
                          className="text-blue-400 hover:text-blue-300 transition-colors duration-200 group p-1 bg-blue-500/10 hover:bg-blue-500/20 rounded-full"
                          whileHover={{ rotate: 180, scale: 1.1 }}
                          transition={{
                            duration: 0.3,
                            type: "spring",
                            stiffness: 200,
                          }}
                        >
                          <RxReload className="w-3.5 h-3.5" />
                        </motion.button>
                      </TooltipTrigger>
                      <TooltipContent side="top">
                        <p className=" text-white text-xs">Start new chat</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
              </div>
            ) : null}
            {!isAgentResponding ? (
              <div className="absolute right-4 bottom-4 flex items-center space-x-2">
                <p className="text-sm text-gray-600">
                  <span className="font-bold">⌘ + Enter</span> to send
                </p>
              </div>
            ) : null}
          </motion.div>

          {isAgentResponding && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.3 }}
              className="absolute top-0 left-0 w-full h-full rounded-xl overflow-hidden backdrop-blur-sm"
            >
              <div className=" h-full w-full flex flex-col items-center justify-center">
                <div className="flex flex-col items-center space-y-1">
                  <div className="flex items-center text-white/90 text-sm font-semibold">
                    <div className="flex items-center bg-gradient-to-r from-blue-400 to-cyan-300 text-transparent bg-clip-text">
                      <Image
                        src="/logo_vector_transparent.png"
                        alt="Sky Logo"
                        width={20}
                        height={20}
                        className="mr-1"
                      />
                      <span>Sky is responding</span>
                    </div>
                    <span className="flex ml-1">
                      <motion.span
                        animate={{ opacity: [0, 1, 0] }}
                        transition={{
                          duration: 1.2,
                          repeat: Infinity,
                          repeatDelay: 0,
                        }}
                      >
                        .
                      </motion.span>
                      <motion.span
                        animate={{ opacity: [0, 1, 0] }}
                        transition={{
                          duration: 1.2,
                          repeat: Infinity,
                          repeatDelay: 0.2,
                        }}
                      >
                        .
                      </motion.span>
                      <motion.span
                        animate={{ opacity: [0, 1, 0] }}
                        transition={{
                          duration: 1.2,
                          repeat: Infinity,
                          repeatDelay: 0.4,
                        }}
                      >
                        .
                      </motion.span>
                    </span>
                  </div>
                </div>

                <div className="flex items-center mt-5">
                  <div className="flex items-center space-x-2 p-0.5">
                    {handleCancelResponse && (
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <motion.button
                              type="button"
                              onClick={handleCancelResponse}
                              className="text-red-400 hover:text-red-300 transition-colors duration-200 flex items-center space-x-1 px-3 py-1.5 bg-red-500/10 hover:bg-red-500/20 rounded-md"
                              whileHover={{ scale: 1.03 }}
                              whileTap={{ scale: 0.97 }}
                            >
                              <MdStop className="w-4 h-4" />
                              <span className="text-xs font-medium">Stop</span>
                            </motion.button>
                          </TooltipTrigger>
                          <TooltipContent side="top">
                            <p className="text-xs">Stop current response</p>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    )}

                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <motion.button
                            type="button"
                            onClick={handleReloadChat}
                            className="text-blue-400 hover:text-blue-300 transition-colors duration-200 flex items-center space-x-1 px-3 py-1.5 bg-blue-500/10 hover:bg-blue-500/20 rounded-md"
                            whileHover={{ scale: 1.03 }}
                            whileTap={{ scale: 0.97 }}
                          >
                            <MdRefresh className="w-4 h-4" />
                            <span className="text-xs font-medium">
                              New Chat
                            </span>
                          </motion.button>
                        </TooltipTrigger>
                        <TooltipContent side="top">
                          <p className="text-xs">Start a new conversation</p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </div>
      </form>
    </div>
  );
};

export default ChatInput;

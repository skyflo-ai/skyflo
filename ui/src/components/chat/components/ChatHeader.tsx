import { HiMiniSparkles } from "react-icons/hi2";

const ChatHeader = () => {
  return (
    <div className="space-y-6 mb-10 relative">
      <div className="flex items-center justify-center">
        <div
          className="bg-gradient-to-br from-blue-800/20 to-blue-700/20 p-3 rounded-md
              shadow-lg shadow-blue-800/10 backdrop-blur-sm"
        >
          <HiMiniSparkles className="w-4 h-4 text-blue-400" />
        </div>
        <div className="ml-3 text-center">
          <h1 className="text-4xl font-bold tracking-tight text-gray-100">
            Hi! I'm{" "}
            <span className="bg-gradient-to-r from-blue-400 via-cyan-400 to-blue-500 bg-clip-text text-transparent px-1 relative">
              Sky
              <span className="absolute -bottom-0.5 left-0 right-0 h-px bg-gradient-to-r from-blue-400/0 via-blue-400/50 to-blue-400/0"></span>
            </span>
          </h1>
        </div>
      </div>
      <div className="text-center space-y-4">
        <p className="text-gray-400 text-xs max-w-md mx-auto leading-relaxed font-semibold tracking-wide">
          Your AI-Powered Cloud Native Co-Pilot
        </p>
      </div>
    </div>
  );
};

export default ChatHeader;

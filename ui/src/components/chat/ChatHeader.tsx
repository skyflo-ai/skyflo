const ChatHeader = () => {
  return (
    <div className="relative mb-10 space-y-6">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 flex items-start justify-center"
      >
        <div className="mt-[-2rem] h-40 w-[32rem] bg-gradient-to-r from-[#1A2C48]/50 via-[#0F182A]/60 to-[#1A2C48]/50 blur-3xl" />
      </div>

      <div className="text-center">
        <h1 className="text-4xl font-bold tracking-tight text-gray-100">
          I'm{" "}
          <span className="relative whitespace-nowrap px-1">
            <span className="bg-gradient-to-r from-[#00B7FF] via-[#0094E8] to-[#0056B3] bg-clip-text text-transparent">
              Sky
            </span>
          </span>
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-gray-400">
          Your DevOps Copilot for Kubernetes & Jenkins
        </p>
      </div>
    </div>
  );
};

export default ChatHeader;

import Image from "next/image";

export default function Loader() {
  return (
    <div className="flex flex-col items-center justify-center gap-6">
      {/* Animated spinner with logo */}
      <div className="relative w-28 h-28 flex items-center justify-center">
        {/* Outer spinning ring */}
        <div className="absolute inset-0 border-4 border-slate-700/60 rounded-full"></div>
        <div
          className="absolute inset-0 border-4 border-t-blue-600 border-r-cyan-600 border-b-slate-700/40 border-l-slate-700/40 rounded-full animate-spin"
          style={{ animationDuration: "2s" }}
        ></div>

        {/* Middle ring with reverse animation */}
        <div className="absolute inset-[6px] border-4 border-slate-700/60 rounded-full"></div>
        <div
          className="absolute inset-[6px] border-4 border-b-blue-500 border-l-cyan-500 border-t-slate-700/40 border-r-slate-700/40 rounded-full animate-spin"
          style={{ animationDuration: "3s", animationDirection: "reverse" }}
        ></div>

        {/* Inner pulsing core with logo */}
        <div
          className="absolute inset-[14px] bg-gradient-to-br from-[#1A2C48]/90 to-[#0F182A]/90 rounded-full animate-pulse"
          style={{ animationDuration: "1.5s" }}
        ></div>
        <div className="absolute inset-[14px] flex items-center justify-center">
          <Image
            src="/logo_vector_transparent.png"
            alt="Skyflo.ai"
            width={40}
            height={40}
            className="rounded-full"
          />
        </div>
      </div>

      {/* Cycling text messages */}
      <div className="h-6 overflow-hidden relative w-64 text-center">
        <ul className="cycling-text text-blue-400 animate-cycling-text absolute w-full list-none m-0 p-0">
          <li className="h-6 flex justify-center items-center">
            Scanning environment
          </li>
          <li className="h-6 flex justify-center items-center">
            Initializing neural pathways
          </li>
          <li className="h-6 flex justify-center items-center">
            Connecting to the cluster
          </li>
          <li className="h-6 flex justify-center items-center">
            Loading cloud interface
          </li>
          <li className="h-6 flex justify-center items-center">
            Ready to assist
          </li>
        </ul>
      </div>

      {/* Add CSS for cycling text animation */}
      <style jsx global>{`
        @keyframes cycleText {
          0%,
          16% {
            transform: translateY(0);
          }
          16.6%,
          33% {
            transform: translateY(-24px);
          }
          33.6%,
          50% {
            transform: translateY(-48px);
          }
          50.6%,
          66% {
            transform: translateY(-72px);
          }
          66.6%,
          83% {
            transform: translateY(-96px);
          }
          83.6%,
          100% {
            transform: translateY(-120px);
          }
        }

        .animate-cycling-text {
          animation: cycleText 3s infinite;
          animation-timing-function: cubic-bezier(0.8, 0, 0.2, 1);
        }
      `}</style>
    </div>
  );
}

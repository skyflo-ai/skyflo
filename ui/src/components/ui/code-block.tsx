import React, { useState } from "react";
import { MdCheck, MdContentCopy } from "react-icons/md";
import { cn } from "@/lib/utils";
import { ScrollArea } from "@/components/ui/scroll-area";

interface CodeBlockProps {
  code: string;
  className?: string;
}

export function CodeBlock({ code, className }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={cn("relative group", className)}>
      <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 via-transparent to-transparent opacity-50 rounded-xl overflow-hidden" />

      <div className="relative">
        <button
          onClick={handleCopy}
          className="absolute top-2 right-4 z-10 opacity-0 group-hover:opacity-100 transition-opacity duration-200 p-2 bg-gray-800 hover:bg-gray-700 rounded-full shadow-[0px_0px_6px_5px_rgba(0,_0,_0,_0.1)]"
          aria-label="Copy code"
        >
          {copied ? (
            <MdCheck className="h-4 w-4 text-green-500" />
          ) : (
            <MdContentCopy className="h-4 w-4 text-gray-300" />
          )}
        </button>

        <ScrollArea className="relative max-h-[300px] overflow-y-auto">
          <pre
            className={cn(
              "p-4 font-mono text-sm whitespace-pre-wrap break-words break-all max-w-full overflow-x-hidden bg-blue-500/5"
            )}
          >
            <code className="text-gray-300 leading-6 whitespace-pre-wrap break-words break-all max-w-full block">
              {code}
            </code>
          </pre>
        </ScrollArea>
      </div>
    </div>
  );
}

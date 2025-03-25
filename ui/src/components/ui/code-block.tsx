import React, { useState } from "react";
import { Check, Copy } from "lucide-react";
import { cn } from "@/lib/utils";
import { ScrollArea } from "@/components/ui/scroll-area";

interface CodeBlockProps {
  code: string;
  language?: string;
  showLineNumbers?: boolean;
  className?: string;
}

export function CodeBlock({
  code,
  language = "bash",
  showLineNumbers = false,
  className,
}: CodeBlockProps) {
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
        <div className="flex items-center justify-between px-2 py-1 border-b border-blue-500/10">
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 rounded-full bg-red-500/20" />
            <div className="w-3 h-3 rounded-full bg-yellow-500/20" />
            <div className="w-3 h-3 rounded-full bg-green-500/20" />
          </div>
          {language && (
            <span className="text-xs text-gray-400 font-mono">{language}</span>
          )}
          <button
            onClick={handleCopy}
            className="opacity-0 group-hover:opacity-100 transition-opacity duration-200 
                     p-1 hover:bg-blue-500/10 rounded-lg"
            aria-label="Copy code"
          >
            {copied ? (
              <Check className="h-4 w-4 text-green-500" />
            ) : (
              <Copy className="h-4 w-4 text-gray-400" />
            )}
          </button>
        </div>

        <ScrollArea className="relative max-h-[300px] overflow-y-auto">
          <pre
            className={cn(
              "p-4 overflow-x-auto font-mono text-sm",
              showLineNumbers && "pl-12 relative"
            )}
          >
            {showLineNumbers && (
              <div className="absolute left-0 top-0 bottom-0 w-8 bg-blue-500/5 flex flex-col items-end pr-2 text-gray-500 select-none">
                {code.split("\n").map((_, i) => (
                  <div key={i} className="leading-6">
                    {i + 1}
                  </div>
                ))}
              </div>
            )}
            <code className="text-gray-300 leading-6">{code}</code>
          </pre>
        </ScrollArea>
      </div>
    </div>
  );
}

import { ReactNode } from "react";
import { CodeBlock } from "./code-block";

interface MarkdownProps {
  node?: unknown;
  children?: ReactNode;
}

interface CodeProps extends MarkdownProps {
  inline?: boolean;
  className?: string;
}

export const markdownComponents = {
  h1: ({ node, ...props }: MarkdownProps) => (
    <h1
      className="text-2xl tracking-wide leading-loose text-white font-bold my-6 border-b border-gray-600 pb-2"
      {...props}
    />
  ),
  h2: ({ node, ...props }: MarkdownProps) => (
    <h2
      className="text-xl tracking-wide leading-loose text-white font-semibold my-5"
      {...props}
    />
  ),
  h3: ({ node, ...props }: MarkdownProps) => (
    <h3
      className="text-lg tracking-wide leading-loose text-white font-medium my-4"
      {...props}
    />
  ),
  h4: ({ node, ...props }: MarkdownProps) => (
    <h4
      className="text-base tracking-wide leading-loose text-white font-medium my-3"
      {...props}
    />
  ),
  p: ({ node, ...props }: MarkdownProps) => (
    <p
      className="text-md tracking-wide leading-relaxed text-white mb-4"
      {...props}
    />
  ),
  code: ({ node, inline, className, children, ...props }: CodeProps) => {
    const match = /language-(\w+)/.exec(className || "");
    const language = match ? match[1] : undefined;

    if (
      inline ||
      (!language && typeof children === "string" && !children.includes("\n"))
    ) {
      return (
        <code
          className="bg-gray-800 leading-loose text-pink-500 px-2 py-1 rounded-md"
          {...props}
        >
          {children}
        </code>
      );
    }

    return (
      <CodeBlock code={String(children).replace(/\n$/, "")} className="my-4" />
    );
  },
  ul: ({ node, ...props }: MarkdownProps & { depth?: number }) => {
    const depth = (node as any)?.depth || 0;
    return (
      <ul
        className={`text-md tracking-wide leading-relaxed text-white my-3 ${
          depth === 0 ? "list-disc" : "list-circle"
        } ml-4 marker:text-primary-cyan`}
        {...props}
      />
    );
  },
  ol: ({ node, ...props }: MarkdownProps) => (
    <ol
      className="text-md tracking-wide leading-relaxed text-white my-3 list-decimal ml-6"
      {...props}
    />
  ),
  li: ({ node, ...props }: MarkdownProps) => {
    const depth = (node as any)?.depth || 0;
    return <li className={`my-1 ${depth > 0 ? "pl-4" : ""}`} {...props} />;
  },
  blockquote: ({ node, ...props }: MarkdownProps) => (
    <blockquote
      className="border-l-4 border-blue-500 pl-4 py-2 my-4 bg-blue-900/20 rounded-r-md text-blue-100 italic"
      {...props}
    />
  ),
  a: ({ node, ...props }: MarkdownProps & { href?: string }) => (
    <a
      className="text-blue-400 hover:text-blue-300 underline decoration-blue-500 hover:decoration-blue-400 transition-colors"
      target="_blank"
      rel="noopener noreferrer"
      {...props}
    />
  ),
  table: ({ node, ...props }: MarkdownProps) => (
    <div className="overflow-x-auto my-4">
      <table
        className="min-w-full bg-gray-800 border border-gray-600 rounded-lg"
        {...props}
      />
    </div>
  ),
  thead: ({ node, ...props }: MarkdownProps) => (
    <thead className="bg-gray-700" {...props} />
  ),
  tbody: ({ node, ...props }: MarkdownProps) => (
    <tbody className="divide-y divide-gray-600" {...props} />
  ),
  tr: ({ node, ...props }: MarkdownProps) => (
    <tr className="hover:bg-gray-700/50 transition-colors" {...props} />
  ),
  th: ({ node, ...props }: MarkdownProps) => (
    <th
      className="px-4 py-2 text-left text-xs font-medium text-gray-300 uppercase tracking-wider border-b border-gray-600"
      {...props}
    />
  ),
  td: ({ node, ...props }: MarkdownProps) => (
    <td
      className="px-4 py-2 text-md text-white border-b border-gray-700"
      {...props}
    />
  ),
  hr: ({ node, ...props }: MarkdownProps) => (
    <hr className="border-gray-600 my-6" {...props} />
  ),
  strong: ({ node, ...props }: MarkdownProps) => (
    <strong className="font-semibold" {...props} />
  ),
  em: ({ node, ...props }: MarkdownProps) => (
    <em className="italic text-blue-200" {...props} />
  ),
};

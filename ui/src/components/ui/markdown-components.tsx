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

// The sub-list should be indented and have a different bullet style
export const markdownComponents = {
  h1: ({ node, ...props }: MarkdownProps) => (
    <h1
      className="text-2xl tracking-wide leading-loose text-white font-bold my-4"
      {...props}
    />
  ),
  h2: ({ node, ...props }: MarkdownProps) => (
    <h2
      className="text-xl tracking-wide leading-loose text-white font-semibold my-4"
      {...props}
    />
  ),
  h3: ({ node, ...props }: MarkdownProps) => (
    <h3
      className="text-md tracking-wide leading-loose text-white font-medium my-4"
      {...props}
    />
  ),
  p: ({ node, ...props }: MarkdownProps) => (
    <p className="text-sm tracking-wide leading-loose text-white" {...props} />
  ),
  code: ({ node, inline, className, children, ...props }: CodeProps) => {
    const match = /language-(\w+)/.exec(className || "");
    const language = match ? match[1] : undefined;

    // Single backtick code is inline and has no language class
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
      <CodeBlock
        code={String(children).replace(/\n$/, "")}
        language={language}
        showLineNumbers={true}
        className="my-4"
      />
    );
  },
  ul: ({ node, ...props }: MarkdownProps & { depth?: number }) => {
    const depth = (node as any)?.depth || 0;
    return (
      <ul
        className={`text-sm tracking-wide leading-loose text-white my-2 ${
          depth === 0 ? "list-disc" : "list-circle"
        } list-inside`}
        {...props}
      />
    );
  },
  li: ({ node, ...props }: MarkdownProps) => {
    const depth = (node as any)?.depth || 0;
    return (
      <li className={` my-1 ${depth === 0 ? "pl-2" : "pl-6"}`} {...props} />
    );
  },
};

import { ReactNode } from "react";
import Header from "./Header";

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  return (
    <div className="  bg-gray-900 text-gray-100">
      <Header />
      <main>{children}</main>
    </div>
  );
}

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import React from "react";

interface AuthInputProps {
  id: string;
  type: string;
  name: string;
  placeholder: string;
  icon: React.ComponentType<{ className?: string; size?: number }>;
}

export const AuthInput: React.FC<AuthInputProps> = ({
  id,
  type,
  name,
  placeholder,
  icon: Icon,
}) => (
  <div className="space-y-1 mb-4">
    <Label htmlFor={id} className="text-sm font-medium text-gray-300">
      {name}
    </Label>
    <div className="relative">
      <div className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 rounded-full flex items-center justify-center">
        <Icon className="h-4 w-4 text-white" />
      </div>
      <Input
        id={id}
        type={type}
        name={name.toLowerCase()}
        placeholder={placeholder}
        required
        className="w-full p-3 pl-10 rounded-lg bg-gray-800 border border-slate-700/60 text-slate-300 shadow-inner outline-none focus:outline-none focus-visible:outline-none focus:border-slate-500/60 focus:ring-2 focus:ring-slate-500/20 transition-[border-color,box-shadow] duration-200"
      />
    </div>
  </div>
);

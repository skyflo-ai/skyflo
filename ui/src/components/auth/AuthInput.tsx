import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LucideIcon } from "lucide-react";

interface AuthInputProps {
  id: string;
  type: string;
  name: string;
  placeholder: string;
  icon: LucideIcon;
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
        className="bg-gray-700 border-gray-600 text-white placeholder-gray-400 pl-12 pr-4 py-2 rounded-lg transition-all duration-200 autofill:bg-gray-900 autofill:text-white"
      />
    </div>
  </div>
);

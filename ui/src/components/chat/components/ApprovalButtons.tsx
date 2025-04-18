import { motion } from "framer-motion";
import { MdThumbUp, MdThumbDown } from "react-icons/md";
import { Button } from "@/components/ui/button";

interface ApprovalButtonsProps {
  onApprove: (stepId: string) => void;
  onReject: (stepId: string) => void;
  parameters: any;
  tool: string;
  action: string;
  step: { id: string };
  setExpandedSteps: React.Dispatch<
    React.SetStateAction<Record<string, boolean>>
  >;
}

const ApprovalButtons: React.FC<ApprovalButtonsProps> = ({
  onApprove,
  onReject,
  parameters,
  tool,
  action,
  step,
  setExpandedSteps,
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="mt-4 space-y-4"
    >
      <div className="bg-gradient-to-br from-slate-800/80 to-slate-900/80 p-6 rounded-lg border border-slate-700/60 shadow-lg backdrop-blur-sm">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-2 h-2 bg-amber-500/80 rounded-full animate-pulse" />
          <h4 className="text-sm font-medium bg-gradient-to-r from-amber-200/90 to-amber-100/90 bg-clip-text text-transparent">
            Approval Required
          </h4>
        </div>
        <div className="text-sm text-slate-300 mb-4 space-y-3">
          <p>This operation requires your approval before execution.</p>
        </div>
        <div className="flex gap-2 justify-end">
          <motion.div whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }}>
            <Button
              onClick={() => {
                onApprove(step.id);
                // Add a small delay before collapsing to allow the approval action to complete
                setTimeout(() => {
                  setExpandedSteps((prev) => ({
                    ...prev,
                    [step.id]: false,
                  }));
                }, 300);
              }}
              className="bg-gradient-to-b from-emerald-950/90 to-emerald-900/90 hover:from-emerald-900/90 hover:to-emerald-800/90 text-emerald-300 border border-emerald-800/30 shadow-sm shadow-emerald-900/20 flex items-center gap-2 px-4 py-2 h-9 transition-all duration-200 backdrop-blur-sm"
            >
              <motion.div
                initial={{ rotate: 0 }}
                whileHover={{ rotate: 10 }}
                transition={{ duration: 0.2 }}
              >
                <MdThumbUp className="w-4 h-4" />
              </motion.div>
              Approve
            </Button>
          </motion.div>
          <motion.div whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }}>
            <Button
              onClick={() => {
                onReject(step.id);
                // Add a small delay before collapsing to allow the rejection action to complete
                setTimeout(() => {
                  setExpandedSteps((prev) => ({
                    ...prev,
                    [step.id]: false,
                  }));
                }, 300);
              }}
              variant="destructive"
              className="bg-gradient-to-b from-rose-950/90 to-rose-900/90 hover:from-rose-900/90 hover:to-rose-800/90 text-rose-300 border border-rose-800/30 shadow-sm shadow-rose-900/20 flex items-center gap-2 px-4 py-2 h-9 transition-all duration-200 backdrop-blur-sm"
            >
              <motion.div
                initial={{ rotate: 0 }}
                whileHover={{ rotate: -10 }}
                transition={{ duration: 0.2 }}
              >
                <MdThumbDown className="w-4 h-4" />
              </motion.div>
              Reject
            </Button>
          </motion.div>
        </div>
      </div>
    </motion.div>
  );
};

export default ApprovalButtons;

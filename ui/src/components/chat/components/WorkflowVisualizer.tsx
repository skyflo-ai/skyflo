import { useEffect, useState, useRef, useCallback } from "react";
import { WorkflowPhase, WorkflowVisualizerProps } from "../types";
import { AgentState } from "../types";
import {
  MdCheck,
  MdKeyboardArrowRight,
  MdKeyboardArrowDown,
} from "react-icons/md";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";
import Markdown from "react-markdown";
import { markdownComponents } from "@/components/ui/markdown-components";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import { HiMiniSparkles } from "react-icons/hi2";
import ApprovalButtons from "./ApprovalButtons";
import {
  getPhaseStatus,
  getPlanningSteps,
  getExecutionSteps,
  getVerificationSteps,
  getResponseSteps,
  getStatusIcon,
  hasStepsForPhase,
} from "../utils/workflowUtils";

// Animation variants
const fadeInVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.4 } },
};

// Phase type display mapping
const PHASE_TYPE_DISPLAY: Record<string, string> = {
  planning: "Planning Workflow",
  executing: "Executing Steps",
  verifying: "Verifying Results",
  responding: "Generating Final Response",
};

const expandVariants = {
  collapsed: { height: 0, opacity: 0, overflow: "hidden" },
  expanded: {
    height: "auto",
    opacity: 1,
    transition: {
      height: { duration: 0.3 },
      opacity: { duration: 0.2, delay: 0.1 },
    },
  },
};

export function WorkflowVisualizer({
  currentPlan,
  executionSteps,
  validationResults,
  currentPhase,
  currentAgentState,
  loadingStatusMessage,
  terminalOutputs,
  finalResponse,
  onApprove,
  onReject,
}: WorkflowVisualizerProps) {
  const [phases, setPhases] = useState<WorkflowPhase[]>([]);
  const [expandedSteps, setExpandedSteps] = useState<Record<string, boolean>>(
    {}
  );
  const [expandedPhases, setExpandedPhases] = useState<Record<string, boolean>>(
    {
      planning: true,
      executing: true,
      verifying: true,
    }
  );

  // Create a more robust tracking system for handled approval steps using both step_id and component id
  const [handledStepIds, setHandledStepIds] = useState<Set<string>>(new Set());

  // Store the original raw step IDs from the API for reference
  const rawStepIdsRef = useRef<Set<string>>(new Set());

  // Ref for auto-scrolling
  const bottomRef = useRef<HTMLDivElement>(null);

  // Function to scroll to bottom
  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  // Update raw step IDs when execution steps change
  useEffect(() => {
    executionSteps.forEach((step) => {
      if (step.step_id) {
        rawStepIdsRef.current.add(step.step_id);
      }
    });
  }, [executionSteps]);

  // Update the approval handlers with the improved step tracking
  const handleApprove = useCallback(
    (stepId: string) => {
      onApprove?.(stepId);

      // Add both the component ID and any matching raw step_id to the handled set
      setHandledStepIds((prev) => {
        const newSet = new Set(prev);
        newSet.add(stepId);

        // If this is a transformed ID (like "exec-0"), find and add the original step_id too
        if (stepId.startsWith("exec-")) {
          const index = parseInt(stepId.replace("exec-", ""));
          if (executionSteps[index]?.step_id) {
            newSet.add(executionSteps[index].step_id);
          }
        }
        return newSet;
      });

      // Add a small delay before collapsing to allow the approval action to complete
      setTimeout(() => {
        setExpandedSteps((prev) => ({
          ...prev,
          [stepId]: false,
        }));
      }, 300);
    },
    [onApprove, executionSteps]
  );

  const handleReject = useCallback(
    (stepId: string) => {
      onReject?.(stepId);

      // Add both the component ID and any matching raw step_id to the handled set
      setHandledStepIds((prev) => {
        const newSet = new Set(prev);
        newSet.add(stepId);

        // If this is a transformed ID (like "exec-0"), find and add the original step_id too
        if (stepId.startsWith("exec-")) {
          const index = parseInt(stepId.replace("exec-", ""));
          if (executionSteps[index]?.step_id) {
            newSet.add(executionSteps[index].step_id);
          }
        }
        return newSet;
      });

      // Add a small delay before collapsing to allow the rejection action to complete
      setTimeout(() => {
        setExpandedSteps((prev) => ({
          ...prev,
          [stepId]: false,
        }));
      }, 300);
    },
    [onReject, executionSteps]
  );

  // Helper function to check if a step has been handled
  const isStepHandled = useCallback(
    (step: any) => {
      // Check if the step ID is in our handled set
      if (handledStepIds.has(step.id)) {
        return true;
      }

      // If this is an execution step, also check the original step_id
      if (step.type === "execution" && step.details?.step_id) {
        return handledStepIds.has(step.details.step_id);
      }

      return false;
    },
    [handledStepIds]
  );

  // Update the useEffect to consider handled steps
  useEffect(() => {
    // Get the transformed execution steps to match the IDs used in the component
    const transformedExecutionSteps = getExecutionSteps(
      executionSteps,
      currentAgentState,
      terminalOutputs
    );

    // Auto-expand steps that require approval and haven't been handled
    const stepsRequiringApproval = transformedExecutionSteps
      .filter((step) => step.approval_required && !isStepHandled(step))
      .map((step) => step.id);

    if (stepsRequiringApproval.length > 0) {
      scrollToBottom();
      setExpandedSteps((prev) => ({
        ...prev,
        ...stepsRequiringApproval.reduce(
          (acc, stepId) => ({
            ...acc,
            [stepId]: true,
          }),
          {}
        ),
      }));

      // Also expand the executing phase if it contains steps requiring approval
      setExpandedPhases((prev) => ({
        ...prev,
        executing: true,
      }));
    }
  }, [
    executionSteps,
    isStepHandled,
    scrollToBottom,
    currentAgentState,
    terminalOutputs,
  ]);

  // Toggle expanded state for a step
  const toggleStepExpanded = (stepId: string) => {
    setExpandedSteps((prev) => ({
      ...prev,
      [stepId]: !prev[stepId],
    }));
  };

  // Toggle expanded state for a phase
  const togglePhaseExpanded = (phaseType: string) => {
    setExpandedPhases((prev) => ({
      ...prev,
      [phaseType]: !prev[phaseType],
    }));
  };

  // Update phases when props change
  useEffect(() => {
    const newPhases: WorkflowPhase[] = [
      {
        type: "planning",
        status: getPhaseStatus(
          "planning",
          currentPhase,
          currentAgentState,
          validationResults
        ),
        steps: getPlanningSteps(
          currentPlan,
          executionSteps,
          currentPhase,
          currentAgentState,
          terminalOutputs
        ),
        startTime: Date.now(),
      },
      {
        type: "executing",
        status: getPhaseStatus(
          "executing",
          currentPhase,
          currentAgentState,
          validationResults
        ),
        steps: getExecutionSteps(
          executionSteps,
          currentAgentState,
          terminalOutputs
        ),
        startTime: currentPhase === "executing" ? Date.now() : undefined,
      },
      {
        type: "verifying",
        status: getPhaseStatus(
          "verifying",
          currentPhase,
          currentAgentState,
          validationResults
        ),
        steps: getVerificationSteps(
          validationResults,
          currentPlan,
          currentPhase,
          currentAgentState
        ),
        startTime: currentPhase === "verifying" ? Date.now() : undefined,
      },
      {
        type: "responding",
        status: getPhaseStatus(
          "responding",
          currentPhase,
          currentAgentState,
          validationResults
        ),
        steps: getResponseSteps(
          terminalOutputs,
          currentPhase,
          currentAgentState,
          executionSteps
        ),
        startTime: currentPhase === "responding" ? Date.now() : undefined,
      },
    ];
    setPhases(newPhases);
  }, [
    currentPlan,
    executionSteps,
    validationResults,
    currentPhase,
    currentAgentState,
    terminalOutputs,
  ]);

  // Auto-scroll when execution steps, validation results, or phases change
  useEffect(() => {
    // Only auto-scroll if we're in executing or verifying phase
    // to avoid unwanted scrolling during initial load
    if (currentPhase === "executing" || currentPhase === "verifying") {
      scrollToBottom();
    }
  }, [executionSteps, validationResults, currentPhase, scrollToBottom]);

  // Update expandedPhases when agent state or phase changes
  useEffect(() => {
    // Auto-expand the current phase based on the currentPhase prop
    if (currentPhase) {
      setExpandedPhases((prev) => ({
        ...prev,
        [currentPhase]: true,
      }));
    }

    // Always auto-expand responding phase when it's complete or has response data
    if (
      currentAgentState === AgentState.COMPLETED ||
      currentAgentState === AgentState.RESPONDING ||
      currentPhase === "responding" ||
      terminalOutputs.some((output) => output.stepId === "response-generation")
    ) {
      setExpandedPhases((prev) => ({
        ...prev,
        responding: true,
      }));
    }

    // Auto-expand steps in the responding phase
    if (
      currentAgentState === AgentState.COMPLETED ||
      currentAgentState === AgentState.RESPONDING ||
      currentPhase === "responding"
    ) {
      const responseStep = "response-generation";
      setExpandedSteps((prev) => ({
        ...prev,
        [responseStep]: true,
      }));
    }
  }, [currentPhase, currentAgentState, terminalOutputs]);

  // Add this function inside the component, before the return statement
  const checkHasStepsForPhase = (phaseType: string) => {
    return hasStepsForPhase(
      phaseType,
      currentPlan,
      executionSteps,
      validationResults,
      currentPhase,
      currentAgentState,
      terminalOutputs
    );
  };

  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={fadeInVariants}
      className="bg-[#0A1020] rounded-lg border border-[#243147] shadow-xl overflow-hidden max-h-[85vh] w-full"
    >
      <div className="bg-gradient-to-r from-[#1A2C48]/90 to-[#0F182A]/90 p-4 border-b border-[#243147] backdrop-blur-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <HiMiniSparkles className="w-4 h-4 text-blue-400" />
            <h3 className="text-lg font-semibold bg-gradient-to-r from-sky-400 to-indigo-400 bg-clip-text text-transparent">
              Sky
            </h3>
          </div>
        </div>
      </div>

      <div
        className="pt-4 pb-2 px-4 space-y-4 overflow-auto max-h-[calc(85vh-64px)] custom-scrollbar"
        style={{ overflowX: "hidden" }}
      >
        <AnimatePresence>
          {loadingStatusMessage && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="text-sm text-blue-300 mb-2 bg-blue-600/10 p-3 rounded-lg border border-blue-600/20 backdrop-blur-sm"
            >
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></div>
                <span className="font-medium">Status:</span>{" "}
                {loadingStatusMessage}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="space-y-6">
          {phases.map((phase, phaseIndex) => (
            <motion.div
              key={phase.type}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: phaseIndex * 0.1 }}
              className="relative"
            >
              <motion.div
                className="flex items-center mb-2 cursor-pointer"
                onClick={() => togglePhaseExpanded(phase.type)}
                whileHover={{ x: 5 }}
                transition={{ duration: 0.2 }}
              >
                <motion.div
                  className={cn(
                    "w-6 h-6 rounded-full flex items-center justify-center mr-2",
                    phase.status === "success"
                      ? "bg-emerald-500/20 text-emerald-400 border border-emerald-600/60"
                      : phase.status === "in_progress"
                      ? "bg-blue-600/20 text-blue-400 border border-blue-600/60"
                      : phase.status === "failure"
                      ? "bg-rose-500/20 text-rose-500 border border-rose-600/60"
                      : "bg-slate-700/20 text-slate-400 border border-slate-600/60"
                  )}
                  animate={
                    phase.status === "in_progress"
                      ? {
                          scale: [1, 1.1, 1],
                          transition: { repeat: Infinity, duration: 2 },
                        }
                      : {}
                  }
                >
                  {getStatusIcon(phase.status)}
                </motion.div>
                <h4 className="text-slate-100 font-medium capitalize">
                  {PHASE_TYPE_DISPLAY[phase.type] || phase.type}
                </h4>
                <div className="ml-auto">
                  {expandedPhases[phase.type] ? (
                    <MdKeyboardArrowDown className="text-blue-400" />
                  ) : (
                    <MdKeyboardArrowRight className="text-blue-400" />
                  )}
                </div>
              </motion.div>

              <AnimatePresence initial={false}>
                {expandedPhases[phase.type] && (
                  <motion.div
                    initial="collapsed"
                    animate="expanded"
                    exit="collapsed"
                    variants={expandVariants}
                    className="ml-8 space-y-2"
                  >
                    {checkHasStepsForPhase(phase.type) &&
                    phase.steps.length > 0 ? (
                      phase.steps.map((step, stepIndex) => (
                        <motion.div
                          key={step.id}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{
                            delay: stepIndex * 0.05,
                            duration: 0.3,
                          }}
                          className="overflow-hidden"
                        >
                          <motion.div
                            className={cn(
                              "border rounded-lg transition-all duration-300 overflow-hidden",
                              step.status === "success"
                                ? "border-emerald-600/40 shadow-[0_0_15px_rgba(16,185,129,0.1)]"
                                : step.status === "in_progress"
                                ? "border-blue-600/40 shadow-[0_0_15px_rgba(59,130,246,0.1)]"
                                : step.status === "failure"
                                ? "border-rose-600/40 shadow-[0_0_15px_rgba(239,68,68,0.1)]"
                                : "border-slate-700/40"
                            )}
                            whileHover={{
                              y: -2,
                              boxShadow: "0 4px 12px rgba(0,0,0,0.2)",
                              borderColor:
                                step.status === "success"
                                  ? "rgba(16, 185, 129, 0.6)"
                                  : step.status === "in_progress"
                                  ? "rgba(59, 130, 246, 0.6)"
                                  : step.status === "failure"
                                  ? "rgba(239, 68, 68, 0.6)"
                                  : "rgba(51, 65, 85, 0.6)",
                            }}
                          >
                            <motion.div
                              className={cn(
                                "p-3 cursor-pointer",
                                step.status === "success"
                                  ? "bg-gradient-to-r from-emerald-500/15 to-emerald-500/5"
                                  : step.status === "in_progress"
                                  ? "bg-gradient-to-r from-blue-600/15 to-blue-600/5 animate-pulse"
                                  : step.status === "failure"
                                  ? "bg-gradient-to-r from-rose-500/15 to-rose-500/5"
                                  : "bg-gradient-to-r from-slate-800/70 to-slate-900/70"
                              )}
                              onClick={() => toggleStepExpanded(step.id)}
                            >
                              <div className="flex items-start justify-between">
                                <div className="flex items-center">
                                  <motion.div
                                    className={cn(
                                      "w-5 h-5 rounded-full flex items-center justify-center mr-2",
                                      step.status === "success"
                                        ? "text-emerald-400"
                                        : step.status === "in_progress"
                                        ? "text-blue-400"
                                        : step.status === "failure"
                                        ? "text-rose-500"
                                        : "text-slate-500"
                                    )}
                                    animate={
                                      step.status === "in_progress"
                                        ? {
                                            scale: [1, 1.2, 1],
                                            transition: {
                                              repeat: Infinity,
                                              duration: 1.5,
                                            },
                                          }
                                        : {}
                                    }
                                  >
                                    {getStatusIcon(step.status)}
                                  </motion.div>
                                  <div>
                                    <div className="text-sm font-medium text-slate-100">
                                      {step.title}
                                    </div>
                                    <div className="text-xs text-slate-400 mt-1">
                                      {step.description}
                                    </div>
                                  </div>
                                </div>
                                <div>
                                  {expandedSteps[step.id] ? (
                                    <MdKeyboardArrowDown
                                      className={cn(
                                        step.status === "success"
                                          ? "text-emerald-400"
                                          : step.status === "in_progress"
                                          ? "text-blue-400"
                                          : step.status === "failure"
                                          ? "text-rose-400"
                                          : "text-slate-400"
                                      )}
                                    />
                                  ) : (
                                    <MdKeyboardArrowRight
                                      className={cn(
                                        step.status === "success"
                                          ? "text-emerald-400"
                                          : step.status === "in_progress"
                                          ? "text-blue-400"
                                          : step.status === "failure"
                                          ? "text-rose-400"
                                          : "text-slate-400"
                                      )}
                                    />
                                  )}
                                </div>
                              </div>
                            </motion.div>

                            <AnimatePresence initial={false}>
                              {expandedSteps[step.id] && (
                                <motion.div
                                  initial="collapsed"
                                  animate="expanded"
                                  exit="collapsed"
                                  variants={expandVariants}
                                  className="bg-[#0A1628]/80 p-4 border-t border-slate-700/50"
                                >
                                  {step.type === "plan" && step.details && (
                                    <div className="text-xs">
                                      <div className="grid grid-cols-2 gap-2 mb-2">
                                        <div>
                                          <span className="text-slate-400">
                                            Tool:
                                          </span>{" "}
                                          <span className="text-sky-300 font-mono">
                                            {step.details.tool}
                                          </span>
                                        </div>
                                        {step.details.action && (
                                          <div>
                                            <span className="text-slate-400">
                                              Action:
                                            </span>{" "}
                                            <span className="text-sky-300 font-mono">
                                              {step.details.action}
                                            </span>
                                          </div>
                                        )}
                                      </div>
                                      {step.details.parameters && (
                                        <div className="mb-2">
                                          <div className="text-slate-400 mb-1">
                                            Parameters:
                                          </div>
                                          {step.details.tool ===
                                          "create_manifest" ? (
                                            <div>
                                              <div className="text-slate-400 text-xs mb-1">
                                                Manifest Name:{" "}
                                                <span className="text-sky-300 font-mono">
                                                  {
                                                    step.details.parameters
                                                      .manifest_name
                                                  }
                                                </span>
                                              </div>
                                              <div className="text-slate-400 text-xs mb-2">
                                                YAML Content:
                                              </div>
                                              <pre className="text-emerald-300 font-mono bg-[#0F1D2F] p-3 rounded-md overflow-x-auto max-w-full text-xs shadow-inner border border-emerald-600/30 break-all whitespace-pre">
                                                {
                                                  step.details.parameters
                                                    .yaml_content
                                                }
                                              </pre>
                                            </div>
                                          ) : (
                                            <pre className="text-sky-300 font-mono bg-[#0F1D2F] p-2 rounded-md overflow-x-auto max-w-full text-xs shadow-inner border border-slate-700/60 break-all whitespace-pre-wrap">
                                              {JSON.stringify(
                                                step.details.parameters,
                                                null,
                                                2
                                              )}
                                            </pre>
                                          )}
                                        </div>
                                      )}

                                      {step.details.output && (
                                        <div className="mb-2">
                                          <div className="text-slate-400 mb-1">
                                            Output:
                                          </div>
                                          <pre className="text-emerald-300 font-mono bg-[#0F1D2F] p-2 rounded-md overflow-x-auto max-w-full text-xs shadow-inner border border-slate-700/60 break-all whitespace-pre-wrap">
                                            {step.details.output}
                                          </pre>
                                        </div>
                                      )}

                                      {step.details.outputs &&
                                        step.details.outputs.length > 0 && (
                                          <div>
                                            <div className="text-slate-400 mb-1">
                                              Terminal Outputs:
                                            </div>
                                            {step.details.outputs.map(
                                              (output, i) => (
                                                <motion.div
                                                  key={i}
                                                  className="mb-2 border border-slate-700/60 rounded-md overflow-hidden shadow-md"
                                                  initial={{
                                                    opacity: 0,
                                                    y: 10,
                                                  }}
                                                  animate={{ opacity: 1, y: 0 }}
                                                  transition={{
                                                    delay: i * 0.1,
                                                  }}
                                                >
                                                  <div className="bg-[#0A1525] p-2 text-cyan-300 font-mono text-xs border-b border-slate-700/60 flex justify-between items-center">
                                                    <code>
                                                      {output.command}
                                                    </code>
                                                    <span className="text-[10px] text-slate-500">
                                                      {new Date(
                                                        output.timestamp
                                                      ).toLocaleTimeString()}
                                                    </span>
                                                  </div>
                                                  <pre className="text-cyan-300 font-mono bg-[#0A1525]/70 p-2 rounded-b-md overflow-x-auto max-w-full text-xs break-all whitespace-pre-wrap">
                                                    {output.output ||
                                                      "No output"}
                                                  </pre>
                                                </motion.div>
                                              )
                                            )}
                                          </div>
                                        )}
                                    </div>
                                  )}

                                  {step.type === "execution" &&
                                    step.details && (
                                      <div className="text-xs">
                                        <div className="grid grid-cols-2 gap-2 mb-2">
                                          <div>
                                            <span className="text-slate-400 text-sm">
                                              Tool:
                                            </span>{" "}
                                            <span className="text-sky-300 font-mono text-sm">
                                              {step.details.tool}
                                            </span>
                                          </div>
                                          <div>
                                            <span className="text-slate-400 text-sm">
                                              Action:
                                            </span>{" "}
                                            <span className="text-sky-300 font-mono text-sm">
                                              {step.details.action}
                                            </span>
                                          </div>
                                        </div>

                                        {step.details.parameters &&
                                          Object.keys(step.details.parameters)
                                            .length > 0 && (
                                            <div className="mb-2">
                                              <div className="text-slate-400 mb-1 text-sm">
                                                Parameters:
                                              </div>
                                              {(step.type as string) ===
                                                "execution" &&
                                              step.details.tool ===
                                                "create_manifest" ? (
                                                <div>
                                                  <div className="text-slate-400 text-sm mb-1">
                                                    Manifest Name:{" "}
                                                    <span className="text-sky-300 font-mono">
                                                      {
                                                        step.details.parameters
                                                          .manifest_name
                                                      }
                                                    </span>
                                                  </div>
                                                  <div className="text-slate-400 text-sm mb-2">
                                                    YAML Content:
                                                  </div>
                                                  <pre className="text-emerald-300 font-mono bg-[#0F1D2F] p-3 rounded-md overflow-x-auto max-w-full text-sm shadow-inner border border-emerald-600/30 break-all whitespace-pre">
                                                    {
                                                      step.details.parameters
                                                        .yaml_content
                                                    }
                                                  </pre>
                                                </div>
                                              ) : (
                                                <pre className="text-sky-300 font-mono bg-[#0F1D2F] p-2 rounded-md overflow-x-auto max-w-full text-sm shadow-inner border border-slate-700/60 break-all whitespace-pre-wrap">
                                                  {JSON.stringify(
                                                    step.details.parameters,
                                                    null,
                                                    2
                                                  )}
                                                </pre>
                                              )}
                                            </div>
                                          )}

                                        {step.details.output && (
                                          <div className="mb-2">
                                            <div className="text-slate-400 mb-1 text-sm">
                                              Output:
                                            </div>
                                            <pre className="text-emerald-300 font-mono bg-[#0F1D2F] p-2 rounded-md overflow-x-auto max-w-full text-sm shadow-inner border border-slate-700/60 break-all whitespace-pre-wrap">
                                              {step.details.output}
                                            </pre>
                                          </div>
                                        )}

                                        {step.details.outputs &&
                                          step.details.outputs.length > 0 && (
                                            <div>
                                              <div className="text-slate-400 mb-1 text-sm">
                                                Terminal Outputs:
                                              </div>
                                              {step.details.outputs.map(
                                                (output, i) => (
                                                  <motion.div
                                                    key={i}
                                                    className="mb-2 border border-slate-700/60 rounded-md overflow-hidden shadow-md"
                                                    initial={{
                                                      opacity: 0,
                                                      y: 10,
                                                    }}
                                                    animate={{
                                                      opacity: 1,
                                                      y: 0,
                                                    }}
                                                    transition={{
                                                      delay: i * 0.1,
                                                    }}
                                                  >
                                                    <div className="bg-[#0A1525] p-2 text-cyan-300 font-mono text-sm border-b border-slate-700/60 flex justify-between items-center">
                                                      <code>
                                                        {output.command}
                                                      </code>
                                                      <span className="text-[10px] text-slate-500">
                                                        {new Date(
                                                          output.timestamp
                                                        ).toLocaleTimeString()}
                                                      </span>
                                                    </div>
                                                    <pre className="text-cyan-300 font-mono bg-[#0A1525]/70 p-2 rounded-b-md overflow-x-auto max-w-full text-sm break-all whitespace-pre-wrap">
                                                      {output.output ||
                                                        "No output"}
                                                    </pre>
                                                  </motion.div>
                                                )
                                              )}
                                            </div>
                                          )}
                                      </div>
                                    )}

                                  {step.type === "verification" &&
                                    step.details && (
                                      <div className="text-xs">
                                        <div className="mb-2">
                                          <span className="text-slate-400 text-sm">
                                            Criteria:
                                          </span>{" "}
                                          <span className="text-sky-300 text-sm">
                                            {step.details.criterion}
                                          </span>
                                        </div>

                                        <div className="mb-2">
                                          <span className="text-slate-400 text-sm">
                                            Status:
                                          </span>{" "}
                                          <span
                                            className={cn(
                                              step.status === "success"
                                                ? "text-emerald-400 font-medium"
                                                : step.status === "failure"
                                                ? "text-rose-500"
                                                : step.status === "in_progress"
                                                ? "text-blue-400"
                                                : "text-slate-300"
                                            )}
                                          >
                                            {step.status === "success"
                                              ? "✓ Success"
                                              : step.status === "failure"
                                              ? "✗ Failed"
                                              : step.status === "in_progress"
                                              ? "In Progress"
                                              : "Pending"}
                                          </span>
                                        </div>

                                        {step.details.details && (
                                          <div className="mb-2">
                                            <span className="text-slate-400 text-sm">
                                              Result:
                                            </span>{" "}
                                            <span
                                              className={cn(
                                                step.status === "success"
                                                  ? "text-emerald-400"
                                                  : step.status === "failure"
                                                  ? "text-rose-500"
                                                  : "text-slate-300"
                                              )}
                                            >
                                              {step.details.details}
                                            </span>
                                          </div>
                                        )}
                                      </div>
                                    )}

                                  {step.type === "response" && step.details && (
                                    <div className="text-xs">
                                      <div className="mb-2">
                                        <span className="text-slate-400 text-sm">
                                          Status:
                                        </span>{" "}
                                        <span
                                          className={
                                            step.status === "success"
                                              ? "text-emerald-400 font-medium"
                                              : "text-blue-400"
                                          }
                                        >
                                          {step.status === "success"
                                            ? "Completed"
                                            : "In Progress"}
                                        </span>
                                      </div>

                                      {!finalResponse &&
                                        !step.details.outputs?.length &&
                                        step.details.output && (
                                          <div className="mb-2">
                                            <div className="text-slate-400 mb-1 text-sm">
                                              Output:
                                            </div>
                                            <pre className="text-emerald-300 font-mono bg-[#0F1D2F] p-2 rounded-md overflow-x-auto max-w-full text-xs shadow-inner border border-slate-700/60 break-all whitespace-pre-wrap">
                                              {step.details.output}
                                            </pre>
                                          </div>
                                        )}

                                      {finalResponse &&
                                        finalResponse.length > 0 && (
                                          <div className="mb-2">
                                            <div className="text-slate-400 mb-1 text-sm">
                                              Final Response:
                                            </div>
                                            <Markdown
                                              components={markdownComponents}
                                              remarkPlugins={[
                                                remarkGfm,
                                                remarkBreaks,
                                              ]}
                                            >
                                              {finalResponse}
                                            </Markdown>
                                          </div>
                                        )}
                                    </div>
                                  )}

                                  {/* Only show approval buttons if this step hasn't been handled yet */}
                                  {step.approval_required &&
                                    !isStepHandled(step) && (
                                      <ApprovalButtons
                                        onApprove={handleApprove}
                                        onReject={handleReject}
                                        parameters={step.details.parameters}
                                        tool={step.details.tool}
                                        action={step.details.action}
                                        step={step}
                                        setExpandedSteps={setExpandedSteps}
                                      />
                                    )}

                                  <div className="text-xs text-slate-500 mt-3 flex justify-end">
                                    {step.timestamp && (
                                      <span>
                                        {new Date(
                                          step.timestamp
                                        ).toLocaleTimeString()}
                                      </span>
                                    )}
                                  </div>
                                </motion.div>
                              )}
                            </AnimatePresence>
                          </motion.div>
                        </motion.div>
                      ))
                    ) : (
                      <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="text-sm text-slate-500 italic p-2 bg-slate-800/30 rounded-md border border-slate-700/60"
                      >
                        {phase.type === "executing" &&
                        currentPhase === "executing"
                          ? "Preparing to execute steps..."
                          : phase.type === "responding" &&
                            (currentPhase === "responding" ||
                              currentAgentState === AgentState.RESPONDING)
                          ? "Generating final response from execution results..."
                          : "No steps available for this phase yet"}
                      </motion.div>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>

              {phaseIndex < phases.length - 1 && expandedPhases[phase.type] && (
                <div className="absolute left-3 top-8 bottom-0 w-px bg-gradient-to-b from-blue-500/40 to-transparent -mb-4" />
              )}
            </motion.div>
          ))}
        </div>

        <AnimatePresence>
          {currentAgentState === AgentState.COMPLETED && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="border-t border-slate-700/60 p-4 bg-gradient-to-r from-emerald-600/15 to-emerald-600/5 rounded-md"
            >
              <div className="text-emerald-400 font-medium flex items-center">
                <MdCheck className="mr-1" /> Workflow completed successfully
              </div>
              <div className="text-sm text-emerald-400/70 mt-2">
                {executionSteps.length} steps executed |{" "}
                {validationResults.length} criteria verified
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <style jsx global>{`
          .custom-scrollbar::-webkit-scrollbar {
            width: 5px;
            height: 5px;
          }
          .custom-scrollbar::-webkit-scrollbar-track {
            background: rgba(15, 29, 47, 0.3);
            border-radius: 10px;
          }
          .custom-scrollbar::-webkit-scrollbar-thumb {
            background: rgba(59, 130, 246, 0.6);
            border-radius: 10px;
          }
          .custom-scrollbar::-webkit-scrollbar-thumb:hover {
            background: rgba(59, 130, 246, 0.8);
          }
        `}</style>

        <div ref={bottomRef} />
      </div>
    </motion.div>
  );
}

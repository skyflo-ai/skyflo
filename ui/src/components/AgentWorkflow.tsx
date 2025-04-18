"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { FaBrain, FaRunning, FaShieldAlt } from "react-icons/fa";
import { HiArrowRight } from "react-icons/hi";

// Agent states
export enum AgentState {
  IDLE = "idle",
  PLANNING = "planning",
  EXECUTING = "executing",
  VERIFYING = "verifying",
  COMPLETED = "completed",
  ERROR = "error",
}

interface AgentWorkflowProps {
  currentState: AgentState;
  planDescription?: string;
  executionDescription?: string;
  verificationDescription?: string;
}

export function AgentWorkflow({
  currentState,
  planDescription = "Analyzing your request and determining the best approach",
  executionDescription = "Executing operations in your Kubernetes environment",
  verificationDescription = "Verifying results and ensuring everything is working correctly",
}: AgentWorkflowProps) {
  const [plannerActive, setPlannerActive] = useState(false);
  const [executorActive, setExecutorActive] = useState(false);
  const [verifierActive, setVerifierActive] = useState(false);
  const [plannerComplete, setPlannerComplete] = useState(false);
  const [executorComplete, setExecutorComplete] = useState(false);
  const [verifierComplete, setVerifierComplete] = useState(false);

  useEffect(() => {
    switch (currentState) {
      case AgentState.PLANNING:
        setPlannerActive(true);
        setExecutorActive(false);
        setVerifierActive(false);
        setPlannerComplete(false);
        setExecutorComplete(false);
        setVerifierComplete(false);
        break;
      case AgentState.EXECUTING:
        setPlannerActive(false);
        setExecutorActive(true);
        setVerifierActive(false);
        setPlannerComplete(true);
        setExecutorComplete(false);
        setVerifierComplete(false);
        break;
      case AgentState.VERIFYING:
        setPlannerActive(false);
        setExecutorActive(false);
        setVerifierActive(true);
        setPlannerComplete(true);
        setExecutorComplete(true);
        setVerifierComplete(false);
        break;
      case AgentState.COMPLETED:
        setPlannerActive(false);
        setExecutorActive(false);
        setVerifierActive(false);
        setPlannerComplete(true);
        setExecutorComplete(true);
        setVerifierComplete(true);
        break;
      case AgentState.ERROR:
        // Handle error state
        break;
      default:
        setPlannerActive(false);
        setExecutorActive(false);
        setVerifierActive(false);
        setPlannerComplete(false);
        setExecutorComplete(false);
        setVerifierComplete(false);
    }
  }, [currentState]);

  const getNodeColor = (isActive: boolean, isComplete: boolean) => {
    if (isActive) return "from-blue-600/30 to-blue-500/30 border-blue-500/50";
    if (isComplete)
      return "from-green-600/20 to-green-500/20 border-green-500/30";
    return "from-gray-800/30 to-gray-700/30 border-gray-700/30";
  };

  const getTextColor = (isActive: boolean, isComplete: boolean) => {
    if (isActive) return "text-blue-400";
    if (isComplete) return "text-green-400";
    return "text-gray-500";
  };

  const getIconColor = (isActive: boolean, isComplete: boolean) => {
    if (isActive) return "text-blue-400";
    if (isComplete) return "text-green-400";
    return "text-gray-600";
  };

  const getConnectorColor = (isActive: boolean, isComplete: boolean) => {
    if (isActive) return "bg-blue-500";
    if (isComplete) return "bg-green-500";
    return "bg-gray-700";
  };

  return (
    <div className="w-full py-4">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between w-full space-y-4 md:space-y-0 md:space-x-4">
        {/* Planner Node */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className={`relative flex flex-col items-center w-full md:w-1/3 p-4 rounded-xl bg-gradient-to-br ${getNodeColor(
            plannerActive,
            plannerComplete
          )} border ${plannerActive ? "shadow-lg shadow-blue-500/10" : ""}`}
        >
          <div className="flex items-center justify-center w-10 h-10 rounded-full bg-gray-900/80 mb-3">
            <FaBrain
              className={`w-5 h-5 ${getIconColor(
                plannerActive,
                plannerComplete
              )}`}
            />
          </div>
          <h3
            className={`text-md font-bold ${getTextColor(
              plannerActive,
              plannerComplete
            )}`}
          >
            Planner
          </h3>
          <p className="text-xs text-gray-400 text-center mt-2">
            {planDescription}
          </p>

          {plannerActive && (
            <div className="absolute -bottom-1 left-1/2 transform -translate-x-1/2 translate-y-full">
              <div className="animate-pulse flex space-x-1">
                <div className="w-1 h-1 bg-blue-400 rounded-full"></div>
                <div className="w-1 h-1 bg-blue-400 rounded-full animate-delay-100"></div>
                <div className="w-1 h-1 bg-blue-400 rounded-full animate-delay-200"></div>
              </div>
            </div>
          )}
        </motion.div>

        {/* Connector 1 */}
        <div className="hidden md:flex items-center justify-center w-12">
          <div
            className={`h-1 w-full ${getConnectorColor(
              executorActive || executorComplete,
              executorComplete
            )}`}
          >
            <HiArrowRight
              className={`w-5 h-5 ${getIconColor(
                executorActive,
                executorComplete
              )}`}
            />
          </div>
        </div>

        {/* Executor Node */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.1 }}
          className={`relative flex flex-col items-center w-full md:w-1/3 p-4 rounded-xl bg-gradient-to-br ${getNodeColor(
            executorActive,
            executorComplete
          )} border ${executorActive ? "shadow-lg shadow-blue-500/10" : ""}`}
        >
          <div className="flex items-center justify-center w-10 h-10 rounded-full bg-gray-900/80 mb-3">
            <FaRunning
              className={`w-5 h-5 ${getIconColor(
                executorActive,
                executorComplete
              )}`}
            />
          </div>
          <h3
            className={`text-md font-bold ${getTextColor(
              executorActive,
              executorComplete
            )}`}
          >
            Executor
          </h3>
          <p className="text-xs text-gray-400 text-center mt-2">
            {executionDescription}
          </p>

          {executorActive && (
            <div className="absolute -bottom-1 left-1/2 transform -translate-x-1/2 translate-y-full">
              <div className="animate-pulse flex space-x-1">
                <div className="w-1 h-1 bg-blue-400 rounded-full"></div>
                <div className="w-1 h-1 bg-blue-400 rounded-full animate-delay-100"></div>
                <div className="w-1 h-1 bg-blue-400 rounded-full animate-delay-200"></div>
              </div>
            </div>
          )}
        </motion.div>

        {/* Connector 2 */}
        <div className="hidden md:flex items-center justify-center w-12">
          <div
            className={`h-1 w-full ${getConnectorColor(
              verifierActive || verifierComplete,
              verifierComplete
            )}`}
          >
            <HiArrowRight
              className={`w-5 h-5 ${getIconColor(
                verifierActive,
                verifierComplete
              )}`}
            />
          </div>
        </div>

        {/* Verifier Node */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.2 }}
          className={`relative flex flex-col items-center w-full md:w-1/3 p-4 rounded-xl bg-gradient-to-br ${getNodeColor(
            verifierActive,
            verifierComplete
          )} border ${verifierActive ? "shadow-lg shadow-blue-500/10" : ""}`}
        >
          <div className="flex items-center justify-center w-10 h-10 rounded-full bg-gray-900/80 mb-3">
            <FaShieldAlt
              className={`w-5 h-5 ${getIconColor(
                verifierActive,
                verifierComplete
              )}`}
            />
          </div>
          <h3
            className={`text-md font-bold ${getTextColor(
              verifierActive,
              verifierComplete
            )}`}
          >
            Verifier
          </h3>
          <p className="text-xs text-gray-400 text-center mt-2">
            {verificationDescription}
          </p>

          {verifierActive && (
            <div className="absolute -bottom-1 left-1/2 transform -translate-x-1/2 translate-y-full">
              <div className="animate-pulse flex space-x-1">
                <div className="w-1 h-1 bg-blue-400 rounded-full"></div>
                <div className="w-1 h-1 bg-blue-400 rounded-full animate-delay-100"></div>
                <div className="w-1 h-1 bg-blue-400 rounded-full animate-delay-200"></div>
              </div>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}

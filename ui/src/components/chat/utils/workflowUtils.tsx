import React, { ReactNode } from "react";
import { MdCheck, MdError, MdInfo, MdPlayArrow } from "react-icons/md";
import { AgentState, WorkflowPhase, WorkflowStep } from "../types";

export function getPhaseStatus(
  phase: string,
  currentPhase: string,
  currentAgentState: AgentState,
  validationResults: any[]
): "pending" | "in_progress" | "success" | "failure" {
  const allValidationsSuccessful =
    validationResults.length > 0 &&
    validationResults.every((r) => r.status === "success");

  if (currentAgentState === AgentState.COMPLETED) {
    return "success";
  }

  if (phase === "responding") {
    if (currentPhase === "responding") {
      return "in_progress";
    }
    if (currentAgentState === AgentState.RESPONDING) {
      return "success";
    }
    return "pending";
  }

  if (phase === "verifying") {
    if (allValidationsSuccessful) {
      return "success";
    }

    if (currentPhase === "verifying" && !allValidationsSuccessful) {
      return "in_progress";
    }
  }

  if (currentPhase === phase) {
    return "in_progress";
  }

  if (
    (currentPhase === "verifying" ||
      currentPhase === "responding" ||
      allValidationsSuccessful) &&
    (phase === "planning" || phase === "executing")
  ) {
    return "success";
  }

  if (currentPhase === "") return "pending";

  const phaseOrder = ["planning", "executing", "verifying", "responding"];
  const currentIndex = phaseOrder.indexOf(currentPhase);
  const phaseIndex = phaseOrder.indexOf(phase);

  if (phaseIndex < currentIndex) return "success";

  return "pending";
}

export function getPlanningSteps(
  currentPlan: any,
  executionSteps: any[],
  currentPhase: string,
  currentAgentState: AgentState,
  terminalOutputs: any[]
): WorkflowStep[] {
  if (!currentPlan) return [];

  return (currentPlan.steps || []).map((step: any, index: number) => {
    const matchingExecutionStep = executionSteps.find(
      (execStep) =>
        (step.step_id && execStep.step_id === step.step_id) ||
        execStep.step_id === `${index + 1}` ||
        execStep.tool === step.tool ||
        (index === 0 &&
          executionSteps.length > 0 &&
          execStep === executionSteps[0])
    );

    const firstExecutionStep =
      index === 0 && executionSteps.length > 0 ? executionSteps[0] : null;

    let status: "pending" | "in_progress" | "success" | "failure";
    if (matchingExecutionStep) {
      status =
        matchingExecutionStep.status === "completed"
          ? "success"
          : matchingExecutionStep.status === "failed"
          ? "failure"
          : "in_progress";
    } else {
      status =
        currentPhase === "planning"
          ? "in_progress"
          : currentPhase === "executing" || currentPhase === "verifying"
          ? "success"
          : currentAgentState === AgentState.COMPLETED
          ? "success"
          : "pending";
    }

    const stepOutputs = matchingExecutionStep
      ? terminalOutputs.filter(
          (output) => output.stepId === matchingExecutionStep.step_id
        )
      : [];

    const outputSource =
      matchingExecutionStep || (index === 0 ? firstExecutionStep : null);

    return {
      id: `plan-${index}`,
      type: "plan",
      status,
      title: `Step ${index + 1}`,
      description: step.description || step.tool,
      details: {
        ...step,
        output: outputSource?.output || "",
        outputs: stepOutputs,
        action: outputSource?.action || "",
      },
      timestamp: Date.now(),
    };
  });
}

export function getExecutionSteps(
  executionSteps: any[],
  currentAgentState: AgentState,
  terminalOutputs: any[]
): WorkflowStep[] {
  return executionSteps.map((step, index) => {
    const stepOutputs = terminalOutputs.filter(
      (output) => output.stepId === step.step_id
    );

    return {
      id: step.step_id || `exec-${index}`,
      type: "execution",
      status:
        step.status === "completed" ||
        currentAgentState === AgentState.COMPLETED
          ? "success"
          : step.status === "failed"
          ? "failure"
          : step.status === "executing"
          ? "in_progress"
          : "pending",
      title: `${step.tool} - ${step.action || "execute"}`,
      description: step.description,
      details: {
        ...step,
        outputs: stepOutputs,
      },
      timestamp: step.timestamp,
      approval_required: step.approval_required,
    };
  });
}

export function getVerificationSteps(
  validationResults: any[],
  currentPlan: any,
  currentPhase: string,
  currentAgentState: AgentState
): WorkflowStep[] {
  if (validationResults.length > 0) {
    const allSuccessful = validationResults.every(
      (result) => result.status === "success"
    );

    return validationResults.map((result, index) => ({
      id: `verify-${index}`,
      type: "verification",
      status:
        currentAgentState === AgentState.COMPLETED ||
        result.status === "success" ||
        (currentPhase === "verifying" &&
          allSuccessful &&
          result.status !== "failure")
          ? "success"
          : result.status === "failure"
          ? "failure"
          : currentPhase === "verifying"
          ? "in_progress"
          : "pending",
      title: `Criteria ${index + 1}`,
      description: result.criterion,
      details: result,
      timestamp: Date.now(),
    }));
  }

  if (currentPlan?.validation_criteria?.length) {
    return currentPlan.validation_criteria.map(
      (criterion: string, index: number) => ({
        id: `verify-${index}`,
        type: "verification",
        status:
          currentAgentState === AgentState.COMPLETED
            ? "success"
            : currentPhase === "verifying"
            ? "in_progress"
            : "pending",
        title: `Criteria ${index + 1}`,
        description: criterion,
        details: { criterion, status: "pending" },
        timestamp: Date.now(),
      })
    );
  }

  return [];
}

export function getResponseSteps(
  terminalOutputs: any[],
  currentPhase: string,
  currentAgentState: AgentState,
  executionSteps: any[]
): WorkflowStep[] {
  const responseTerminalOutput = terminalOutputs[terminalOutputs.length - 1];

  if (
    responseTerminalOutput ||
    currentPhase === "responding" ||
    currentAgentState === AgentState.RESPONDING ||
    currentAgentState === AgentState.COMPLETED
  ) {
    let outputContent = "";
    if (responseTerminalOutput) {
      outputContent = responseTerminalOutput.output;
    } else if (executionSteps.length > 0) {
      outputContent = executionSteps[executionSteps.length - 1].output;
    }

    const responseStatus =
      currentAgentState === AgentState.COMPLETED ? "success" : "in_progress";

    return [
      {
        id: "response-generation",
        type: "response",
        status: responseStatus,
        title: "Response Generation",
        description: "Final response based on execution results",
        details: {
          phase: "responding",
          status:
            currentAgentState === AgentState.COMPLETED
              ? "completed"
              : "in_progress",
          output:
            outputContent || "Generating response from execution results...",
          outputs: responseTerminalOutput ? [responseTerminalOutput] : [],
        },
        timestamp: Date.now(),
      },
    ];
  }

  return [];
}

export function getStatusIcon(status: string): ReactNode {
  switch (status) {
    case "success":
      return <MdCheck className="text-emerald-400" />;
    case "in_progress":
      return <MdPlayArrow className="text-blue-400 animate-pulse" />;
    case "failure":
      return <MdError className="text-rose-500" />;
    default:
      return <MdInfo className="text-slate-400" />;
  }
}

export function hasStepsForPhase(
  phaseType: string,
  currentPlan: any,
  executionSteps: any[],
  validationResults: any[],
  currentPhase: string,
  currentAgentState: AgentState,
  terminalOutputs: any[]
): boolean {
  if (phaseType === "planning" && currentPlan?.steps?.length) {
    return true;
  }
  if (phaseType === "executing" && executionSteps.length > 0) {
    return true;
  }
  if (
    phaseType === "verifying" &&
    (validationResults.length > 0 || currentPlan?.validation_criteria?.length)
  ) {
    return true;
  }
  if (
    phaseType === "responding" &&
    (currentPhase === "responding" ||
      currentAgentState === AgentState.RESPONDING ||
      currentAgentState === AgentState.COMPLETED ||
      terminalOutputs.some((output) => output.stepId === "response-generation"))
  ) {
    return true;
  }
  return false;
}

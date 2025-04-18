import React from "react";
import {
  FaCheckCircle,
  FaTimesCircle,
  FaExclamationTriangle,
} from "react-icons/fa";

interface ValidationResult {
  criterion: string;
  status: "success" | "failure" | "warning";
  details?: string;
}

interface VerificationResultsProps {
  results: ValidationResult[];
  overallStatus: "success" | "failure" | "partial" | "pending";
  title?: string;
}

const VerificationResults: React.FC<VerificationResultsProps> = ({
  results,
  overallStatus,
  title = "Verification Results",
}) => {
  const getStatusBadge = () => {
    switch (overallStatus) {
      case "success":
        return (
          <span className="bg-green-900/30 text-green-400 text-xs px-2 py-1 rounded-full">
            All Checks Passed
          </span>
        );
      case "failure":
        return (
          <span className="bg-red-900/30 text-red-400 text-xs px-2 py-1 rounded-full">
            Verification Failed
          </span>
        );
      case "partial":
        return (
          <span className="bg-yellow-900/30 text-yellow-400 text-xs px-2 py-1 rounded-full">
            Partially Verified
          </span>
        );
      default:
        return (
          <span className="bg-blue-900/30 text-blue-400 text-xs px-2 py-1 rounded-full">
            Verification In Progress
          </span>
        );
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "success":
        return <FaCheckCircle className="text-green-500 flex-shrink-0" />;
      case "failure":
        return <FaTimesCircle className="text-red-500 flex-shrink-0" />;
      default:
        return (
          <FaExclamationTriangle className="text-yellow-500 flex-shrink-0" />
        );
    }
  };

  return (
    <div className="bg-gray-900 rounded-lg p-4 space-y-4 border border-gray-800">
      <div className="flex items-center justify-between">
        <h3 className="text-md font-medium text-gray-200">{title}</h3>
        {getStatusBadge()}
      </div>

      <div className="divide-y divide-gray-800">
        {results.map((result, index) => (
          <div key={index} className="py-3 first:pt-0 last:pb-0">
            <div className="flex items-start gap-3">
              <div className="mt-1">{getStatusIcon(result.status)}</div>
              <div>
                <div className="text-sm text-gray-200">{result.criterion}</div>
                {result.details && (
                  <div className="mt-1 text-xs text-gray-400">
                    {result.details}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}

        {results.length === 0 && (
          <div className="py-3 text-sm text-gray-400 italic">
            No verification criteria to display
          </div>
        )}
      </div>
    </div>
  );
};

export default VerificationResults;

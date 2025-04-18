package v1

import (
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// SkyfloAISpec defines the desired state of SkyfloAI
type SkyfloAISpec struct {
	// UI defines configuration for the Skyflo.ai UI component
	UI UISpec `json:"ui"`

	// Engine defines configuration for the Skyflo.ai Engine component
	Engine EngineSpec `json:"engine"`

	// MCP defines configuration for the Skyflo.ai MCP component
	MCP MCPSpec `json:"mcp"`

	// ImagePullSecrets is a list of references to secrets for pulling images
	// +optional
	ImagePullSecrets []corev1.LocalObjectReference `json:"imagePullSecrets,omitempty"`

	// NodeSelector is a selector which must be true for the pod to fit on a node
	// +optional
	NodeSelector map[string]string `json:"nodeSelector,omitempty"`

	// Tolerations are the pod's tolerations
	// +optional
	Tolerations []corev1.Toleration `json:"tolerations,omitempty"`

	// Affinity defines pod affinity/anti-affinity rules
	// +optional
	Affinity *corev1.Affinity `json:"affinity,omitempty"`
}

// UISpec defines configuration for the UI component
type UISpec struct {
	// Image is the UI component container image
	Image string `json:"image"`

	// Replicas is the number of UI pods to run
	// +optional
	Replicas *int32 `json:"replicas,omitempty"`

	// Resources defines compute resources for the UI container
	// +optional
	Resources corev1.ResourceRequirements `json:"resources,omitempty"`

	// Env defines additional environment variables
	// +optional
	Env []corev1.EnvVar `json:"env,omitempty"`
}

// EngineSpec defines configuration for the Engine component
type EngineSpec struct {
	// Image is the Engine container image
	Image string `json:"image"`

	// Replicas is the number of Engine pods to run
	// +optional
	Replicas *int32 `json:"replicas,omitempty"`

	// Resources defines compute resources for the Engine container
	// +optional
	Resources corev1.ResourceRequirements `json:"resources,omitempty"`

	// DatabaseConfig defines PostgreSQL database configuration
	// +optional
	DatabaseConfig *DatabaseConfig `json:"databaseConfig,omitempty"`

	// RedisConfig defines Redis configuration for WebSocket and rate limiting
	// +optional
	RedisConfig *RedisConfig `json:"redisConfig,omitempty"`

	// Env defines additional environment variables
	// +optional
	Env []corev1.EnvVar `json:"env,omitempty"`
}

// MCPSpec defines configuration for the MCP component
type MCPSpec struct {
	// Image is the MCP container image
	Image string `json:"image"`

	// Replicas is the number of MCP pods to run
	// +optional
	Replicas *int32 `json:"replicas,omitempty"`

	// Resources defines compute resources for the MCP container
	// +optional
	Resources corev1.ResourceRequirements `json:"resources,omitempty"`

	// KubeconfigSecret is the name of the secret containing kubeconfig
	// +optional
	KubeconfigSecret string `json:"kubeconfigSecret,omitempty"`

	// Env defines additional environment variables
	// +optional
	Env []corev1.EnvVar `json:"env,omitempty"`
}

// DatabaseConfig defines PostgreSQL configuration
type DatabaseConfig struct {
	// Host is the database host
	Host string `json:"host"`

	// Port is the database port
	Port int32 `json:"port"`

	// Database is the database name
	Database string `json:"database"`

	// SecretName is the name of the secret containing database credentials
	SecretName string `json:"secretName"`
}

// RedisConfig defines Redis configuration
type RedisConfig struct {
	// Host is the Redis host
	Host string `json:"host"`

	// Port is the Redis port
	Port int32 `json:"port"`

	// SecretName is the name of the secret containing Redis credentials
	// +optional
	SecretName string `json:"secretName,omitempty"`
}

// SkyfloAIStatus defines the observed state of SkyfloAI
type SkyfloAIStatus struct {
	// UIStatus defines the status of the UI component
	UIStatus ComponentStatus `json:"uiStatus"`

	// EngineStatus defines the status of the Engine component
	EngineStatus ComponentStatus `json:"engineStatus"`

	// MCPStatus defines the status of the MCP component
	MCPStatus ComponentStatus `json:"mcpStatus"`

	// Conditions represent the latest available observations of the SkyfloAI state
	// +optional
	Conditions []metav1.Condition `json:"conditions,omitempty"`
}

// ComponentStatus defines the status of a component
type ComponentStatus struct {
	// Phase is the current phase of the component
	Phase string `json:"phase"`

	// Message provides additional information about the phase
	// +optional
	Message string `json:"message,omitempty"`

	// ReadyReplicas is the number of pods ready for this component
	ReadyReplicas int32 `json:"readyReplicas"`

	// DesiredReplicas is the desired number of pods for this component
	DesiredReplicas int32 `json:"desiredReplicas"`
}

//+kubebuilder:object:root=true
//+kubebuilder:subresource:status
//+kubebuilder:resource:scope=Namespaced,shortName=sky
//+kubebuilder:printcolumn:name="UI Ready",type=string,JSONPath=`.status.uiStatus.phase`
//+kubebuilder:printcolumn:name="Engine Ready",type=string,JSONPath=`.status.engineStatus.phase`
//+kubebuilder:printcolumn:name="MCP Ready",type=string,JSONPath=`.status.mcpStatus.phase`
//+kubebuilder:printcolumn:name="Age",type="date",JSONPath=".metadata.creationTimestamp"

// SkyfloAI is the Schema for the skyfloais API
type SkyfloAI struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`

	Spec   SkyfloAISpec   `json:"spec,omitempty"`
	Status SkyfloAIStatus `json:"status,omitempty"`
}

//+kubebuilder:object:root=true

// SkyfloAIList contains a list of SkyfloAI
type SkyfloAIList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []SkyfloAI `json:"items"`
}

func init() {
	SchemeBuilder.Register(&SkyfloAI{}, &SkyfloAIList{})
}

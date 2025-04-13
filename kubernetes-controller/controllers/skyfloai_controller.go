package controllers

import (
	"context"

	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	"k8s.io/apimachinery/pkg/util/intstr"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"
	"sigs.k8s.io/controller-runtime/pkg/log"

	skyflov1 "github.com/skyflo-ai/skyflo/kubernetes-controller/engine/v1"
)

// SkyfloAIReconciler reconciles a SkyfloAI object
type SkyfloAIReconciler struct {
	client.Client
	Scheme *runtime.Scheme
}

//+kubebuilder:rbac:groups=skyflo.ai,resources=skyfloais,verbs=get;list;watch;create;update;patch;delete
//+kubebuilder:rbac:groups=skyflo.ai,resources=skyfloais/status,verbs=get;update;patch
//+kubebuilder:rbac:groups=skyflo.ai,resources=skyfloais/finalizers,verbs=update
//+kubebuilder:rbac:groups=apps,resources=deployments,verbs=get;list;watch;create;update;patch;delete
//+kubebuilder:rbac:groups=core,resources=services,verbs=get;list;watch;create;update;patch;delete
//+kubebuilder:rbac:groups=core,resources=secrets,verbs=get;list;watch

// Reconcile is part of the main kubernetes reconciliation loop which aims to
// move the current state of the cluster closer to the desired state.
func (r *SkyfloAIReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	log := log.FromContext(ctx)

	// Fetch the SkyfloAI instance
	skyflo := &skyflov1.SkyfloAI{}
	err := r.Get(ctx, req.NamespacedName, skyflo)
	if err != nil {
		if errors.IsNotFound(err) {
			return ctrl.Result{}, nil
		}
		return ctrl.Result{}, err
	}

	// Reconcile UI component
	if err := r.reconcileUI(ctx, skyflo); err != nil {
		log.Error(err, "failed to reconcile UI component")
		return ctrl.Result{}, err
	}

	// Reconcile Engine component
	if err := r.reconcileEngine(ctx, skyflo); err != nil {
		log.Error(err, "failed to reconcile Engine component")
		return ctrl.Result{}, err
	}

	// Reconcile MCP component
	if err := r.reconcileMCP(ctx, skyflo); err != nil {
		log.Error(err, "failed to reconcile MCP component")
		return ctrl.Result{}, err
	}

	// Update status
	if err := r.updateStatus(ctx, skyflo); err != nil {
		log.Error(err, "failed to update SkyfloAI status")
		return ctrl.Result{}, err
	}

	return ctrl.Result{}, nil
}

// reconcileUI reconciles the UI component
func (r *SkyfloAIReconciler) reconcileUI(ctx context.Context, skyflo *skyflov1.SkyfloAI) error {
	// Create UI deployment
	uiDeployment := r.uiDeployment(skyflo)
	if err := controllerutil.SetControllerReference(skyflo, uiDeployment, r.Scheme); err != nil {
		return err
	}
	if err := r.createOrUpdateDeployment(ctx, uiDeployment); err != nil {
		return err
	}

	// Create UI service
	uiService := r.uiService(skyflo)
	if err := controllerutil.SetControllerReference(skyflo, uiService, r.Scheme); err != nil {
		return err
	}
	if err := r.createOrUpdateService(ctx, uiService); err != nil {
		return err
	}

	return nil
}

// reconcileEngine reconciles the Engine component
func (r *SkyfloAIReconciler) reconcileEngine(ctx context.Context, skyflo *skyflov1.SkyfloAI) error {
	// Create Engine deployment
	engineDeployment := r.engineDeployment(skyflo)
	if err := controllerutil.SetControllerReference(skyflo, engineDeployment, r.Scheme); err != nil {
		return err
	}
	if err := r.createOrUpdateDeployment(ctx, engineDeployment); err != nil {
		return err
	}

	// Create Engine service
	engineService := r.engineService(skyflo)
	if err := controllerutil.SetControllerReference(skyflo, engineService, r.Scheme); err != nil {
		return err
	}
	if err := r.createOrUpdateService(ctx, engineService); err != nil {
		return err
	}

	return nil
}

// reconcileMCP reconciles the MCP component
func (r *SkyfloAIReconciler) reconcileMCP(ctx context.Context, skyflo *skyflov1.SkyfloAI) error {
	// Create MCP deployment
	mcpDeployment := r.mcpDeployment(skyflo)
	if err := controllerutil.SetControllerReference(skyflo, mcpDeployment, r.Scheme); err != nil {
		return err
	}
	if err := r.createOrUpdateDeployment(ctx, mcpDeployment); err != nil {
		return err
	}

	// Create MCP service
	mcpService := r.mcpService(skyflo)
	if err := controllerutil.SetControllerReference(skyflo, mcpService, r.Scheme); err != nil {
		return err
	}
	if err := r.createOrUpdateService(ctx, mcpService); err != nil {
		return err
	}

	return nil
}

// updateStatus updates the status of the SkyfloAI resource
func (r *SkyfloAIReconciler) updateStatus(ctx context.Context, skyflo *skyflov1.SkyfloAI) error {
	// Update UI status
	uiDeployment := &appsv1.Deployment{}
	err := r.Get(ctx, types.NamespacedName{Name: skyflo.Name + "-ui", Namespace: skyflo.Namespace}, uiDeployment)
	if err == nil {
		skyflo.Status.UIStatus = skyflov1.ComponentStatus{
			Phase:           getPhase(uiDeployment),
			ReadyReplicas:   uiDeployment.Status.ReadyReplicas,
			DesiredReplicas: *uiDeployment.Spec.Replicas,
		}
	}

	// Update Engine status
	engineDeployment := &appsv1.Deployment{}
	err = r.Get(ctx, types.NamespacedName{Name: skyflo.Name + "-engine", Namespace: skyflo.Namespace}, engineDeployment)
	if err == nil {
		skyflo.Status.EngineStatus = skyflov1.ComponentStatus{
			Phase:           getPhase(engineDeployment),
			ReadyReplicas:   engineDeployment.Status.ReadyReplicas,
			DesiredReplicas: *engineDeployment.Spec.Replicas,
		}
	}

	// Update MCP status
	mcpDeployment := &appsv1.Deployment{}
	err = r.Get(ctx, types.NamespacedName{Name: skyflo.Name + "-mcp", Namespace: skyflo.Namespace}, mcpDeployment)
	if err == nil {
		skyflo.Status.MCPStatus = skyflov1.ComponentStatus{
			Phase:           getPhase(mcpDeployment),
			ReadyReplicas:   mcpDeployment.Status.ReadyReplicas,
			DesiredReplicas: *mcpDeployment.Spec.Replicas,
		}
	}

	return r.Status().Update(ctx, skyflo)
}

// Helper functions for creating resources

func (r *SkyfloAIReconciler) uiDeployment(skyflo *skyflov1.SkyfloAI) *appsv1.Deployment {
	replicas := int32(1)
	if skyflo.Spec.UI.Replicas != nil {
		replicas = *skyflo.Spec.UI.Replicas
	}

	return &appsv1.Deployment{
		ObjectMeta: metav1.ObjectMeta{
			Name:      skyflo.Name + "-ui",
			Namespace: skyflo.Namespace,
		},
		Spec: appsv1.DeploymentSpec{
			Replicas: &replicas,
			Selector: &metav1.LabelSelector{
				MatchLabels: map[string]string{
					"app": skyflo.Name + "-ui",
				},
			},
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{
					Labels: map[string]string{
						"app": skyflo.Name + "-ui",
					},
				},
				Spec: corev1.PodSpec{
					Containers: []corev1.Container{
						{
							Name:  "ui",
							Image: skyflo.Spec.UI.Image,
							Ports: []corev1.ContainerPort{
								{
									ContainerPort: 3000,
									Name:          "http",
								},
							},
							Resources: skyflo.Spec.UI.Resources,
							Env:       skyflo.Spec.UI.Env,
						},
					},
					ImagePullSecrets: skyflo.Spec.ImagePullSecrets,
					NodeSelector:     skyflo.Spec.NodeSelector,
					Tolerations:      skyflo.Spec.Tolerations,
					Affinity:         skyflo.Spec.Affinity,
				},
			},
		},
	}
}

func (r *SkyfloAIReconciler) uiService(skyflo *skyflov1.SkyfloAI) *corev1.Service {
	return &corev1.Service{
		ObjectMeta: metav1.ObjectMeta{
			Name:      skyflo.Name + "-ui",
			Namespace: skyflo.Namespace,
		},
		Spec: corev1.ServiceSpec{
			Ports: []corev1.ServicePort{
				{
					Port:       80,
					TargetPort: intstr.FromInt(3000),
					Name:       "http",
				},
			},
			Selector: map[string]string{
				"app": skyflo.Name + "-ui",
			},
		},
	}
}

func (r *SkyfloAIReconciler) engineDeployment(skyflo *skyflov1.SkyfloAI) *appsv1.Deployment {
	replicas := int32(1)
	if skyflo.Spec.Engine.Replicas != nil {
		replicas = *skyflo.Spec.Engine.Replicas
	}

	return &appsv1.Deployment{
		ObjectMeta: metav1.ObjectMeta{
			Name:      skyflo.Name + "-engine",
			Namespace: skyflo.Namespace,
		},
		Spec: appsv1.DeploymentSpec{
			Replicas: &replicas,
			Selector: &metav1.LabelSelector{
				MatchLabels: map[string]string{
					"app": skyflo.Name + "-engine",
				},
			},
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{
					Labels: map[string]string{
						"app": skyflo.Name + "-engine",
					},
				},
				Spec: corev1.PodSpec{
					Containers: []corev1.Container{
						{
							Name:  "engine",
							Image: skyflo.Spec.Engine.Image,
							Ports: []corev1.ContainerPort{
								{
									ContainerPort: 8081,
									Name:          "http",
								},
							},
							Resources: skyflo.Spec.Engine.Resources,
							Env:       skyflo.Spec.Engine.Env,
						},
					},
					ImagePullSecrets: skyflo.Spec.ImagePullSecrets,
					NodeSelector:     skyflo.Spec.NodeSelector,
					Tolerations:      skyflo.Spec.Tolerations,
					Affinity:         skyflo.Spec.Affinity,
				},
			},
		},
	}
}

func (r *SkyfloAIReconciler) engineService(skyflo *skyflov1.SkyfloAI) *corev1.Service {
	return &corev1.Service{
		ObjectMeta: metav1.ObjectMeta{
			Name:      skyflo.Name + "-engine",
			Namespace: skyflo.Namespace,
		},
		Spec: corev1.ServiceSpec{
			Ports: []corev1.ServicePort{
				{
					Port:       80,
					TargetPort: intstr.FromInt(8081),
					Name:       "http",
				},
			},
			Selector: map[string]string{
				"app": skyflo.Name + "-engine",
			},
		},
	}
}

func (r *SkyfloAIReconciler) mcpDeployment(skyflo *skyflov1.SkyfloAI) *appsv1.Deployment {
	replicas := int32(1)
	if skyflo.Spec.MCP.Replicas != nil {
		replicas = *skyflo.Spec.MCP.Replicas
	}

	return &appsv1.Deployment{
		ObjectMeta: metav1.ObjectMeta{
			Name:      skyflo.Name + "-mcp",
			Namespace: skyflo.Namespace,
		},
		Spec: appsv1.DeploymentSpec{
			Replicas: &replicas,
			Selector: &metav1.LabelSelector{
				MatchLabels: map[string]string{
					"app": skyflo.Name + "-mcp",
				},
			},
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{
					Labels: map[string]string{
						"app": skyflo.Name + "-mcp",
					},
				},
				Spec: corev1.PodSpec{
					Containers: []corev1.Container{
						{
							Name:  "mcp",
							Image: skyflo.Spec.MCP.Image,
							Ports: []corev1.ContainerPort{
								{
									ContainerPort: 8000,
									Name:          "http",
								},
							},
							Resources: skyflo.Spec.MCP.Resources,
							Env:       skyflo.Spec.MCP.Env,
						},
					},
					ImagePullSecrets: skyflo.Spec.ImagePullSecrets,
					NodeSelector:     skyflo.Spec.NodeSelector,
					Tolerations:      skyflo.Spec.Tolerations,
					Affinity:         skyflo.Spec.Affinity,
				},
			},
		},
	}
}

func (r *SkyfloAIReconciler) mcpService(skyflo *skyflov1.SkyfloAI) *corev1.Service {
	return &corev1.Service{
		ObjectMeta: metav1.ObjectMeta{
			Name:      skyflo.Name + "-mcp",
			Namespace: skyflo.Namespace,
		},
		Spec: corev1.ServiceSpec{
			Ports: []corev1.ServicePort{
				{
					Port:       80,
					TargetPort: intstr.FromInt(8000),
					Name:       "http",
				},
			},
			Selector: map[string]string{
				"app": skyflo.Name + "-mcp",
			},
		},
	}
}

// Helper functions

func (r *SkyfloAIReconciler) createOrUpdateDeployment(ctx context.Context, deployment *appsv1.Deployment) error {
	found := &appsv1.Deployment{}
	err := r.Get(ctx, types.NamespacedName{Name: deployment.Name, Namespace: deployment.Namespace}, found)
	if err != nil {
		if errors.IsNotFound(err) {
			return r.Create(ctx, deployment)
		}
		return err
	}

	deployment.ResourceVersion = found.ResourceVersion
	return r.Update(ctx, deployment)
}

func (r *SkyfloAIReconciler) createOrUpdateService(ctx context.Context, service *corev1.Service) error {
	found := &corev1.Service{}
	err := r.Get(ctx, types.NamespacedName{Name: service.Name, Namespace: service.Namespace}, found)
	if err != nil {
		if errors.IsNotFound(err) {
			return r.Create(ctx, service)
		}
		return err
	}

	service.ResourceVersion = found.ResourceVersion
	service.Spec.ClusterIP = found.Spec.ClusterIP
	return r.Update(ctx, service)
}

func getPhase(deployment *appsv1.Deployment) string {
	if deployment.Status.ReadyReplicas == *deployment.Spec.Replicas {
		return "Ready"
	}
	if deployment.Status.ReadyReplicas > 0 {
		return "Progressing"
	}
	return "Not Ready"
}

// SetupWithManager sets up the controller with the Manager.
func (r *SkyfloAIReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&skyflov1.SkyfloAI{}).
		Owns(&appsv1.Deployment{}).
		Owns(&corev1.Service{}).
		Complete(r)
}

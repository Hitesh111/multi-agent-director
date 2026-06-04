export interface Agent {
  id: number;
  name: string;
  role: string;
  system_prompt: string;
  provider: "deepseek" | "grok" | "gemini" | "openai" | "anthropic" | "opencode";
  model: string;
  tools: string[];
  skills: string[];
  memory_enabled: boolean;
  temperature: number;
  max_iterations: number;
  enabled_channels: string[];
  schedule_config: Record<string, unknown> | null;
  interaction_rules: Record<string, unknown>;
  allowed_agents: number[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface WorkflowNode {
  id: string;
  type: "agent" | "human_approval" | "input" | "output";
  position?: { x: number; y: number };
  data?: Record<string, unknown>;
  agentId?: number;
}

export interface WorkflowEdge {
  source: string;
  target: string;
  condition?: string;
  label?: string;
}

export interface Workflow {
  id: number;
  name: string;
  description: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ExecutionNode {
  id: number;
  node_id: string;
  agent: number | null;
  status: string;
  input_data: Record<string, unknown>;
  output_data: Record<string, unknown> | null;
  error_message: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface Execution {
  id: number;
  workflow: number;
  workflow_name?: string;
  status: string;
  input_data: Record<string, unknown>;
  output_data: Record<string, unknown> | null;
  error_message: string;
  token_usage: Record<string, number>;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  node_states: ExecutionNode[];
}

export interface Message {
  id: number;
  execution: number | null;
  source_agent: number | null;
  source_agent_name?: string;
  role: string;
  content: string;
  token_count: number;
  channel: string;
  created_at: string;
}

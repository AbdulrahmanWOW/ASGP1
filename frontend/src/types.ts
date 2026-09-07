export type Decision = 'ALLOW' | 'BLOCK' | 'ESCALATE'
export interface Session { session_id:string; intent:string; allowed_tools:string[]; forbidden_tools:string[]; allowed_paths:string[]; allowed_destinations:string[]; anchor_version:number; risk_score:number; intent_anchor_hash:string; status:'active'|'revoked'; created_at:string }
export interface AuditEvent { event_id:string; action_id:string; session_id:string; tool_name:string; safe_parameters:Record<string,unknown>; outcome:Decision; reason_codes:string[]; sequence:number; previous_hash:string; entry_hash:string; risk_before:number; risk_after:number; finding_codes:string[]; stage_timings_ms:Record<string,number>; created_at:string }
export interface Approval { approval_id:string; action_id:string; session_id:string; tool_name:string; status:string; expires_at:string; created_at:string; resolved_at:string|null }
export interface RiskChange { action_id:string; session_id:string; previous_score:number; delta:number; new_score:number; reason:string; created_at:string }
export interface Finding { finding_id:string; kind:string; code:string; severity:string; confidence:number; evidence:string; risk_delta:number }
export interface AuditVerification { session_id:string; valid:boolean; event_count:number; verified_hash:string; errors:string[] }
export interface PipelineMetrics { decisions?:number; errors?:number; average_total_latency_ms?:number; outcomes?:Record<string,number>; [key:string]:unknown }

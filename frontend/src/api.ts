import type { Approval, AuditEvent, AuditVerification, Finding, PipelineMetrics, RiskChange, Session } from './types'

const BASE_URL = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1').replace(/\/$/, '')

async function request<T>(path:string, init?:RequestInit):Promise<T>{
  const response=await fetch(`${BASE_URL}${path}`,{...init,headers:{'Content-Type':'application/json',...init?.headers}})
  if(!response.ok){let message=`Request failed (${response.status})`;try{const body=await response.json();message=body.detail||message}catch{/* response was not JSON */}throw new Error(message)}
  return response.json() as Promise<T>
}

export const api={
  health:()=>request<{status:string}>('/health'),
  sessions:()=>request<Session[]>('/sessions'),
  approvals:()=>request<Approval[]>('/approvals'),
  metrics:()=>request<PipelineMetrics>('/metrics/pipeline'),
  audit:(id:string)=>request<AuditEvent[]>(`/audit/${id}`),
  verifyAudit:(id:string)=>request<AuditVerification>(`/audit/${id}/verify`,{method:'POST'}),
  risk:(id:string)=>request<RiskChange[]>(`/risk/${id}`),
  findings:(id:string)=>request<Finding[]>(`/findings/${id}`),
  resolveApproval:(id:string,resolution:'approved'|'rejected')=>request<Approval>(`/approvals/${id}/resolve`,{method:'POST',body:JSON.stringify({resolution})}),
}

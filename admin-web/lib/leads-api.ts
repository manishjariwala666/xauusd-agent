import "server-only";
import { getAdminServerConfig } from "./server-config";

export type LeadSummary={id:number;public_reference:string;name:string;business_email:string;company:string|null;country:string;business_type:string;requested_services:string[];budget_range:string;status:string;created_at:string;updated_at:string;deleted_at:string|null};
export type LeadDetail=LeadSummary&{website_url:string|null;phone:string|null;current_tools:string|null;project_description:string;primary_problem:string;expected_outcome:string;preferred_timeline:string;preferred_contact_method:string;assigned_to:number|null;internal_notes:string|null;consent_recorded_at:string;status_history:{event_type:string;created_at:string;details:Record<string,unknown>}[]};
export type LeadPage={items:LeadSummary[];page:number;page_size:number;total:number;pages:number;stats:Record<string,number>};
async function call<T>(path:string,token:string):Promise<T|null>{if(!token)return null;try{const config=getAdminServerConfig();const response=await fetch(`${config.backendBaseUrl}/admin/leads${path}`,{headers:{Authorization:`Bearer ${token}`,"X-Admin-BFF-Key":config.bffSecret},cache:"no-store",signal:AbortSignal.timeout(5000)});return response.ok?await response.json() as T:null}catch{return null}}
export const fetchLeads=(query:URLSearchParams,token:string)=>call<LeadPage>(`?${query}`,token);
export const fetchLead=(id:string,token:string)=>call<LeadDetail>(`/${encodeURIComponent(id)}`,token);

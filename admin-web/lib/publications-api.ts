import "server-only";
import { getAdminServerConfig } from "./server-config";

export type Announcement={id:number;slug:string;title:string;summary:string;body:string;announcement_type:string;priority:string;audience:string;status:string;featured:boolean;pinned:boolean;cta_label:string|null;cta_url:string|null;media_id:number|null;scheduled_at:string|null;published_at:string|null;expires_at:string|null;updated_at:string};
export type VerifiedResult={id:number;public_id:string;related_signal_id:number|null;symbol:string;direction:"BUY"|"SELL";timeframe:string|null;entry_price:string;exit_price:string;stop_loss:string|null;targets:string[];lifecycle_outcome:string;result_unit:string;result_points:string;evidence_type:string|null;evidence_media_id:number|null;evidence_notes:string|null;redaction_confirmed:boolean;verification_status:string;rejection_reason:string|null;verified_at:string|null;compliance_status:string;compliance_notes:string|null;public_summary:string;featured:boolean;publication_status:string;published_at:string|null;opened_at:string;closed_at:string;updated_at:string};
export type AdminPage<T>={items:T[];page:number;page_size:number;total:number;pages:number;stats:Record<string,number>};
async function call<T>(family:string,path:string,token:string):Promise<T|null>{if(!token)return null;try{const c=getAdminServerConfig();const r=await fetch(`${c.backendBaseUrl}/admin/${family}${path}`,{headers:{Authorization:`Bearer ${token}`,"X-Admin-BFF-Key":c.bffSecret},cache:"no-store",signal:AbortSignal.timeout(5000)});return r.ok?await r.json() as T:null}catch{return null}}
export const fetchAnnouncements=(query:URLSearchParams,token:string)=>call<AdminPage<Announcement>>("announcements",`?${query}`,token);
export const fetchAnnouncement=(id:string,token:string)=>call<Announcement>("announcements",`/${encodeURIComponent(id)}`,token);
export const fetchResults=(query:URLSearchParams,token:string)=>call<AdminPage<VerifiedResult>>("results",`?${query}`,token);
export const fetchResult=(id:string,token:string)=>call<VerifiedResult>("results",`/${encodeURIComponent(id)}`,token);

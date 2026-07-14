import { randomUUID } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import { verifyCsrfToken } from "./csrf";
import { getAdminServerConfig } from "./server-config";
import { ADMIN_CSRF_COOKIE, ADMIN_SESSION_COOKIE } from "./session";
export async function leadProxy(request:NextRequest,path=""){
  if(request.method!=="GET"&&!verifyCsrfToken(request.cookies.get(ADMIN_CSRF_COOKIE)?.value,request.headers.get("x-csrf-token")))return NextResponse.json({message:"Invalid request."},{status:403});
  const token=request.cookies.get(ADMIN_SESSION_COOKIE)?.value||"";if(!token)return NextResponse.json({message:"Authentication required."},{status:401});
  try{const config=getAdminServerConfig();const body=request.method==="GET"?undefined:await request.text();const response=await fetch(`${config.backendBaseUrl}/admin/leads${path}${request.nextUrl.search}`,{method:request.method,headers:{Authorization:`Bearer ${token}`,"X-Admin-BFF-Key":config.bffSecret,"X-Request-ID":randomUUID(),...(body?{"Content-Type":"application/json"}:{})},body,cache:"no-store",signal:AbortSignal.timeout(8000)});return new NextResponse(await response.text()||null,{status:response.status,headers:{"Content-Type":"application/json","Cache-Control":"no-store"}})}catch{return NextResponse.json({message:"Lead service is temporarily unavailable."},{status:503})}
}

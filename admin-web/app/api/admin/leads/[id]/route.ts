import { NextRequest,NextResponse } from "next/server";import { leadProxy } from "@/lib/lead-bff";
async function proxy(request:NextRequest,context:{params:Promise<{id:string}>}){const{id}=await context.params;if(!/^\d+$/.test(id))return NextResponse.json({message:"Not found."},{status:404});return leadProxy(request,`/${id}`)}
export const GET=proxy;export const PATCH=proxy;export const DELETE=proxy;

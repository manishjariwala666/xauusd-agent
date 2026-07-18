import {NextRequest,NextResponse} from "next/server";import {publicationProxy} from "@/lib/publication-bff";
async function proxy(r:NextRequest,c:{params:Promise<{path:string[]}>}){const p=(await c.params).path.join("/");if(!/^\d+(\/transition)?$/.test(p))return NextResponse.json({message:"Not found."},{status:404});return publicationProxy(r,"results",`/${p}`)}
export const GET=proxy;export const PATCH=proxy;export const POST=proxy;export const DELETE=proxy;

import { cookies } from "next/headers";
import { CategoryManager } from "@/components/category-manager";
import { fetchCategories } from "@/lib/content-api";
import { ADMIN_SESSION_COOKIE } from "@/lib/session";

export default async function CategoriesPage() {
  const token = (await cookies()).get(ADMIN_SESSION_COOKIE)?.value || "";
  const data = await fetchCategories(new URLSearchParams({ page_size: "50" }), token);
  return <CategoryManager categories={data?.items || []} />;
}

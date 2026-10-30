// Retired WooCommerce integration; use native Cardyssey API.
export async function POST(){return Response.json({error:"woocommerce_retired",replacement:"/api/admin/shop/native"},{status:410});}

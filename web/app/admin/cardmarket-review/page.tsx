import {redirect} from 'next/navigation';
export default async function CardmarketReviewRedirect({searchParams}:{searchParams:Promise<{search?:string}>}){
 const {search}=await searchParams;
 const query=search?'?review=cardmarket&search='+encodeURIComponent(search):'?review=cardmarket';
 redirect('/admin/prices'+query)
}

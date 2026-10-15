package de.cardyssey.api

import kotlinx.serialization.Serializable
import org.jsoup.Jsoup
import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import java.time.Duration

@Serializable data class AdminPriceLinkInput(val url:String)
@Serializable data class AdminPriceLinkResult(
 val url:String,val domain:String,val title:String?,
 val suggestedPrice:Double?,val currency:String?,
 val status:String,val evidence:String
)

/** Restrictive public-page preview; never turns an asking price into a verified quote. */
class AdminPriceLinkPreview {
 private val client=HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(6))
  .followRedirects(HttpClient.Redirect.NEVER).build()
 private val hosts=setOf("www.cardmarket.com","cardmarket.com","www.tcgplayer.com",
  "tcgplayer.com","www.pricecharting.com","pricecharting.com")
 fun preview(raw:String):AdminPriceLinkResult? {
  if(raw.length>2000)return null
  val uri=runCatching { URI(raw.trim()) }.getOrNull()?:return null
  val host=uri.host?.lowercase()?:return null
  if(uri.scheme!="https"||host !in hosts||uri.port!=-1||uri.userInfo!=null) return null
  val request=HttpRequest.newBuilder(uri).timeout(Duration.ofSeconds(10))
   .header("User-Agent","Mozilla/5.0 CardysseyPriceResearch/1.0")
   .header("Accept","text/html").GET().build()
  val result=runCatching { client.send(request,HttpResponse.BodyHandlers.ofString()) }.getOrNull()
   ?:return AdminPriceLinkResult(raw,host,null,null,null,"UNAVAILABLE","Quelle antwortet derzeit nicht")
  if(result.statusCode()!=200)return AdminPriceLinkResult(raw,host,null,null,null,
   "HTTP_"+result.statusCode(),"Quelle liefert keine öffentlich lesbaren Preisdaten")
  // Cap processed content; ignore arbitrary scripts and private structured fields.
  val doc=Jsoup.parse(result.body().take(650_000),uri.toString())
  val title=doc.title().take(180).ifBlank { null }
  val meta=doc.select("meta[property=product:price:amount],meta[property=og:price:amount],meta[itemprop=price],meta[name=price]").first()
  val priceText=meta?.attr("content")?.takeIf { it.isNotBlank() }
  val currency=doc.select("meta[property=product:price:currency],meta[itemprop=priceCurrency]").first()?.attr("content")?.uppercase()
  val amount=priceText?.replace(",",".")?.toDoubleOrNull()?.takeIf { it.isFinite()&&it>0&&it<10000000 }
  val safeCurrency=currency?.takeIf { it in setOf("EUR","USD","GBP") }
  return AdminPriceLinkResult(raw,host,title,amount,safeCurrency,
   if(amount!=null&&safeCurrency!=null)"PRICE_METADATA_FOUND" else "MANUAL_REVIEW",
   "Produkt- und Preis-Metadaten, kein bestätigter Verkauf. Kartensprache, Variante, Zustand und Edition müssen geprüft werden.")
 }
}

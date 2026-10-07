package de.cardyssey.api

import com.zaxxer.hikari.HikariDataSource
import kotlinx.serialization.Serializable
import java.time.OffsetDateTime

@Serializable data class AdminPriceMonitorItem(val cardId:String,val languageCode:String,val setName:String,val cardName:String,val cardNumber:String,val variantId:String,val variant:String,val lastPriceEur:Double?,val source:String?,val lastSuccessfulSync:String?,val currentStatus:String)
@Serializable data class AdminPriceMonitorCounts(val total:Long,val stale:Long,val noPrice:Long,val providerError:Long)
@Serializable data class AdminPriceMonitorResponse(val counts:AdminPriceMonitorCounts,val items:List<AdminPriceMonitorItem>)

class AdminPriceMonitorRepository(private val dataSource:HikariDataSource) {
 fun openCases(language:String?,status:String?):AdminPriceMonitorResponse {
  val lang=language?.trim()?.lowercase()?.takeIf{it.isNotBlank()&&it!="all"}
  val stat=status?.trim()?.uppercase()?.takeIf{it in setOf("STALE","NO_PRICE","PROVIDER_ERROR")}
  val cte="""WITH variants AS (
 SELECT c.card_id,c.language_code,c.local_id,c.name AS card_name,COALESCE(s.name,c.set_id) AS set_name,
        v.value->>'id' AS variant_id,
        COALESCE(NULLIF(v.value->>'name',''),NULLIF(v.value->>'label',''),NULLIF(v.value->>'legacyVariant',''),v.value->>'id') AS variant_label
 FROM catalog_cards_mirror c
 LEFT JOIN catalog_sets_mirror s ON s.language_code=c.language_code AND s.set_id=c.set_id
 CROSS JOIN LATERAL jsonb_array_elements(c.variants) v(value)
 WHERE c.details_complete=TRUE AND COALESCE(v.value->>'id','')<>'' AND c.set_id !~ '^(A[0-9]|B[0-9]|P-A)'
), monitored AS (
 SELECT v.*,last_success.base_eur AS last_price_eur,last_success.source AS last_source,last_success.captured_at AS last_successful_sync,
 CASE WHEN COALESCE(p.resolution_status,'NO_PRICE')='PROVIDER_ERROR' THEN 'PROVIDER_ERROR'
      WHEN COALESCE(p.resolution_status,'NO_PRICE')='NO_PRICE' THEN 'NO_PRICE'
      WHEN last_success.captured_at IS NULL OR last_success.captured_at < NOW()-INTERVAL '8 days' THEN 'STALE'
      ELSE NULL END AS monitor_status
 FROM variants v
 LEFT JOIN tcg_price_cache p ON p.card_id=v.card_id AND p.language_code=v.language_code AND p.variant_id=v.variant_id
 LEFT JOIN LATERAL (
  SELECT h.base_eur,h.source,h.captured_at FROM tcg_price_history h
  WHERE h.card_id=v.card_id AND h.language_code=v.language_code AND h.variant_id=v.variant_id
  ORDER BY h.captured_at DESC LIMIT 1
 ) last_success ON TRUE
)
"""
  return dataSource.connection.use{connection->
   val counts=connection.prepareStatement(cte+"""SELECT COUNT(*) FILTER(WHERE monitor_status IS NOT NULL) total,
 COUNT(*) FILTER(WHERE monitor_status='STALE') stale,COUNT(*) FILTER(WHERE monitor_status='NO_PRICE') no_price,
 COUNT(*) FILTER(WHERE monitor_status='PROVIDER_ERROR') provider_error FROM monitored""").use{st->
    st.executeQuery().use{r->check(r.next());AdminPriceMonitorCounts(r.getLong("total"),r.getLong("stale"),r.getLong("no_price"),r.getLong("provider_error"))}
   }
   val sql=buildString{append(cte);append("SELECT * FROM monitored WHERE monitor_status IS NOT NULL");if(lang!=null)append(" AND language_code=?");if(stat!=null)append(" AND monitor_status=?");append(" ORDER BY language_code,set_name,card_name,card_id,variant_id")}
   val items=connection.prepareStatement(sql).use{st->var i=1;if(lang!=null)st.setString(i++,lang);if(stat!=null)st.setString(i,stat);st.executeQuery().use{r->buildList{while(r.next())add(AdminPriceMonitorItem(r.getString("card_id"),r.getString("language_code"),r.getString("set_name"),r.getString("card_name"),r.getString("local_id"),r.getString("variant_id"),r.getString("variant_label"),r.getBigDecimal("last_price_eur")?.toDouble(),r.getString("last_source"),r.getObject("last_successful_sync",OffsetDateTime::class.java)?.toString(),r.getString("monitor_status")))}}}
   AdminPriceMonitorResponse(counts,items)
  }
 }
}

package de.cardyssey.api

import com.zaxxer.hikari.HikariDataSource
import kotlinx.serialization.Serializable

@Serializable
data class PriceReviewCase(
 val languageCode:String,val cardId:String,val variantId:String,
 val searchStatus:String,val searchQuery:String?,val searchSteps:String,
 val candidates:String,val failureReason:String?,val checkedAt:String,
 val referencePriceEur:Double?,val referenceSource:String?,val referenceStatus:String?,
 val referenceVerification:String?,val ownerCount:Long,val ownedCopies:Long,
 val cardName:String?,val cardNumber:String?,val setId:String?,val variantDetails:String?,
 val setName:String?,val printedNumber:String?
)

class AdminPriceReviewRepository(private val dataSource:HikariDataSource) {
 fun list(language:String?):List<PriceReviewCase> = dataSource.connection.use { connection ->
  val sql = """SELECT p.language_code,p.card_id,p.variant_id,p.search_status,p.search_query,
      p.search_steps::text,p.candidates::text,p.failure_reason,p.checked_at::text,
      r.price_eur,r.provider,r.verification_status,r.evidence->'verification'->'reasons' AS reference_verification,
      COALESCE(owners.owner_count,0) AS owner_count, COALESCE(owners.owned_copies,0) AS owned_copies,
      catalog.name AS card_name,catalog.local_id AS card_number,catalog.set_id,
      physical.variant::text AS variant_details,
      sets.name AS set_name,CASE WHEN sets.total_count > 0 AND catalog.set_id !~* '^(basep|np|dpp|svp|mep|bwp|swshp|smp|xyp|s-p|sm-p|xy-p)$' THEN catalog.local_id || '/' || sets.total_count::text ELSE catalog.local_id END AS printed_number
      FROM price_review_cases p
      LEFT JOIN price_reference_candidates r ON r.language_code=p.language_code AND r.card_id=p.card_id AND r.variant_id=p.variant_id AND r.provider='POKEMONTCGAPI_REFERENCE'
      LEFT JOIN LATERAL (
        SELECT COUNT(DISTINCT owned.user_id) AS owner_count,SUM(owned.quantity) AS owned_copies
        FROM collection_items owned
        WHERE owned.card_id=p.card_id AND owned.language_code=p.language_code
          AND owned.variant_id=p.variant_id AND owned.deleted_at IS NULL
      ) owners ON TRUE
      LEFT JOIN catalog_cards_mirror catalog ON catalog.language_code=p.language_code
        AND catalog.card_id=p.card_id
      LEFT JOIN catalog_sets_mirror sets ON sets.language_code=p.language_code AND sets.set_id=catalog.set_id
      LEFT JOIN LATERAL (
        SELECT v.value AS variant FROM jsonb_array_elements(catalog.variants) v(value)
        WHERE v.value->>'id'=p.variant_id LIMIT 1
      ) physical ON TRUE
      LEFT JOIN tcg_price_cache c ON c.language_code=p.language_code
        AND c.card_id=p.card_id AND c.variant_id=p.variant_id
      WHERE (c.resolution_status IS NULL OR c.resolution_status <> 'PRICE_FOUND')
        AND (? IS NULL OR p.language_code=?)
      ORDER BY COALESCE(owners.owner_count,0) DESC,COALESCE(owners.owned_copies,0) DESC,
      p.checked_at DESC,p.language_code,p.card_id LIMIT 2000"""
  connection.prepareStatement(sql).use { statement ->
   statement.setString(1,language)
   statement.setString(2,language)
   statement.executeQuery().use { rs ->
    buildList {
     while(rs.next()) add(PriceReviewCase(
      rs.getString(1),rs.getString(2),rs.getString(3),rs.getString(4),rs.getString(5),
      rs.getString(6),rs.getString(7),rs.getString(8),rs.getString(9),
      rs.getBigDecimal(10)?.toDouble(),rs.getString(11),rs.getString(12),rs.getString(13),
      rs.getLong(14),rs.getLong(15),
      rs.getString(16),rs.getString(17),rs.getString(18),rs.getString(19),
      rs.getString(20),rs.getString(21)))
    }
   }
  }
 }
}


# CardPriceQuoteResponse


## Properties

Name | Type
------------ | -------------
`cardId` | string
`languageCode` | string
`variantId` | string
`variantType` | string
`condition` | string
`market` | string
`source` | string
`baseEur` | number
`conditionFactor` | number
`eur` | number
`exactLanguageMatch` | boolean
`exactVariantMatch` | boolean
`sampleCount` | number
`rangeLowEur` | number
`rangeHighEur` | number
`trend30dPercent` | number
`updatedAtMs` | number
`recentSales` | [Array&lt;EbayRecentSaleResponse&gt;](EbayRecentSaleResponse.md)

## Example

```typescript
import type { CardPriceQuoteResponse } from 'cardyssey-contract'

// TODO: Update the object below with actual values
const example = {
  "cardId": null,
  "languageCode": null,
  "variantId": null,
  "variantType": null,
  "condition": null,
  "market": null,
  "source": null,
  "baseEur": null,
  "conditionFactor": null,
  "eur": null,
  "exactLanguageMatch": null,
  "exactVariantMatch": null,
  "sampleCount": null,
  "rangeLowEur": null,
  "rangeHighEur": null,
  "trend30dPercent": null,
  "updatedAtMs": null,
  "recentSales": null,
} satisfies CardPriceQuoteResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as CardPriceQuoteResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)



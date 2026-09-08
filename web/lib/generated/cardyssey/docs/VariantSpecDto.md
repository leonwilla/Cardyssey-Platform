
# VariantSpecDto


## Properties

Name | Type
------------ | -------------
`id` | string
`type` | string
`foil` | string
`size` | string
`subtype` | string
`stamps` | Array&lt;string&gt;

## Example

```typescript
import type { VariantSpecDto } from 'cardyssey-contract'

// TODO: Update the object below with actual values
const example = {
  "id": null,
  "type": null,
  "foil": null,
  "size": null,
  "subtype": null,
  "stamps": null,
} satisfies VariantSpecDto

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as VariantSpecDto
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)



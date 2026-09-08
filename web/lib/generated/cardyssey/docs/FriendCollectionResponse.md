
# FriendCollectionResponse


## Properties

Name | Type
------------ | -------------
`totalValueEur` | number
`cards` | [Array&lt;FriendCollectionCardResponse&gt;](FriendCollectionCardResponse.md)

## Example

```typescript
import type { FriendCollectionResponse } from 'cardyssey-contract'

// TODO: Update the object below with actual values
const example = {
  "totalValueEur": null,
  "cards": null,
} satisfies FriendCollectionResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as FriendCollectionResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)



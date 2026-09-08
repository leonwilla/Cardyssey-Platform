
# FriendRequestsResponse


## Properties

Name | Type
------------ | -------------
`incoming` | [Array&lt;FriendRequestResponse&gt;](FriendRequestResponse.md)
`outgoing` | [Array&lt;FriendRequestResponse&gt;](FriendRequestResponse.md)

## Example

```typescript
import type { FriendRequestsResponse } from 'cardyssey-contract'

// TODO: Update the object below with actual values
const example = {
  "incoming": null,
  "outgoing": null,
} satisfies FriendRequestsResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as FriendRequestsResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)



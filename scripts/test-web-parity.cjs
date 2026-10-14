const { chromium } = require("playwright");
const assert = require("node:assert/strict");
(async () => {
  const base = process.env.CARDYSSEY_TEST_URL || "http://127.0.0.1:3012";
  const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
  try {
    const context = await browser.newContext();
    await context.addCookies([{name:"cardyssey_access",value:"local-test-only",url:base}]);
    const page = await context.newPage();
    const errors=[];
    page.on("pageerror", error=>errors.push(error.message));
    const card={id:"test-001",cardId:"test-001",name:"Testkarte",key:"owned-test",languageCode:"de",
      setId:"test",setName:"Testset",localId:"001",variant:"REVERSE",variantSpec:{id:"reverse-exact",type:"reverse",stamps:[]},
      condition:"GOOD",quantity:3,marketUnitEur:{TCG:1},valuedUnitEur:{TCG:.5},positionValueEur:{TCG:1.5}};
    let posts=[],messages=[],setFails=true;
    await page.route("**/api/**", async route=>{
      const request=route.request(),path=new URL(request.url()).pathname;
      if(path==="/api/auth/me") return route.fulfill({json:{id:"test-user",email:"test@example.invalid",friendCode:"ME"}});
      if(path==="/api/collection") return route.fulfill({json:[card]});
      if(path==="/api/chat/threads") return route.fulfill({json:[{friendCode:"FRIEND",displayName:"Testfreund",unreadCount:0}]});
      if(path==="/api/chat/FRIEND/messages") {
        if(request.method()==="POST") {
          const payload=request.postDataJSON();posts.push(payload);
          messages=[{...payload,id:"message-1",senderFriendCode:"ME",recipientFriendCode:"FRIEND",createdAt:new Date().toISOString()}];
          return route.fulfill({json:messages[0]});
        }
        return route.fulfill({json:messages});
      }
      if(path==="/api/sets/empty") {
        if(setFails) return route.abort("failed");
        return route.fulfill({json:{id:"empty",name:"Testset geladen",officialCount:1,totalCount:1,cards:[]}});
      }
      if(path.startsWith("/api/cards/")) return route.fulfill({json:{...card,variants:[{...card.variantSpec,legacyVariant:"REVERSE"}]}});
      return route.fulfill({json:[]});
    });
    await page.goto(base+"/chat?shareCard=test-001&language=de&collectionKey=owned-test");
    await page.getByText("Testkarte teilen",{exact:true}).waitFor();
    assert.equal(await page.getByRole("button",{name:"Karte jetzt senden",exact:true}).isDisabled(),true);
    await page.getByText("Testfreund",{exact:true}).first().click();
    await page.getByRole("button",{name:"Karte jetzt senden",exact:true}).click();
    await page.getByRole("link",{name:/Testkarte.*Karte ansehen/}).waitFor();
    assert.equal(posts.length,1);
    assert.equal(posts[0].objectPayload.variantSpec.id,"reverse-exact");
    assert.equal(posts[0].objectPayload.languageCode,"de");
    assert.equal(posts[0].objectPayload.condition,"GOOD");
    assert.equal(posts[0].objectPayload.quantity,3);
    assert.equal(posts[0].body,"");
    // A failed set request must leave loading state and allow retry.
    await page.goto(base+"/sets/empty?language=en");
    await page.getByText("Keine Set-Daten verfügbar.").waitFor();
    setFails=false;
    await page.getByRole("button",{name:"Erneut versuchen"}).click();
    await page.getByRole("heading",{name:"Testset geladen"}).waitFor();
    assert.deepEqual(errors,[]);
    console.log("PASS: explicit card sharing, exact variant/condition/quantity, received card display, set error/retry");
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exit(1);});

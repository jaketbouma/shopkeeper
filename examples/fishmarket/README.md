# Example setup of marketplaces

```
╰─ pulumi up                                                                                                                      ─╯
Previewing update (fishmarket)

     Type                                  Name                               Plan       
 +   pulumi:pulumi:Stack                   fishmarket-fishmarket              create     
 +   ├─ pulumi-shopkeeper:index:Market     fishmarketDev                      create     
 +   ├─ aws:s3:BucketV2                    fishmarketDev-bucket               create     
 +   │  ├─ aws:s3:BucketOwnershipControls  fishmarketDev-bucket-writer-owns   create     
 +   │  └─ aws:s3:BucketObjectv2           fishmarketDev-metadata-json        create     
 +   ├─ pulumi-shopkeeper:index:Market     fishmarketProd                     create     
 +   └─ aws:s3:BucketV2                    fishmarketProd-bucket              create     
 +      ├─ aws:s3:BucketObjectv2           fishmarketProd-metadata-json       create     
 +      └─ aws:s3:BucketOwnershipControls  fishmarketProd-bucket-writer-owns  create     

Outputs:
    prodConfig: [unknown]
    testConfig: [unknown]

Resources:
    + 9 to create
```
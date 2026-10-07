const { S3Client, CreateBucketCommand } = require("@aws-sdk/client-s3");

// LocalStack accepts any credentials; these are the ones from the AWS docs.
const s3 = new S3Client({
  endpoint: "http://localhost:4566",
  region: "us-east-1",
  forcePathStyle: true,
  credentials: {
    accessKeyId: "{{FAKE_AWS_DOCS_EXAMPLE}}",
    secretAccessKey: "test",
  },
});

s3.send(new CreateBucketCommand({ Bucket: "uploads-dev" })).then(() => {
  console.log("bucket ready");
});

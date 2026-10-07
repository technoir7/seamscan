const { S3Client, PutObjectCommand } = require("@aws-sdk/client-s3");

const s3 = new S3Client({
  region: "us-east-1",
  credentials: {
    accessKeyId: "{{FAKE_AWS_KEY_ID}}",
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
  },
});

async function uploadAvatar(userId, buffer, contentType) {
  const key = `avatars/${userId}.png`;
  await s3.send(
    new PutObjectCommand({ Bucket: "acme-uploads", Key: key, Body: buffer, ContentType: contentType }),
  );
  return `https://acme-uploads.s3.amazonaws.com/${key}`;
}

module.exports = { uploadAvatar };

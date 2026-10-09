import NextAuth from "next-auth";

export default NextAuth({
  providers: [],
  secret: process.env.NEXT_PUBLIC_SECRET,
});

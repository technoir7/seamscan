export async function searchVideos(query) {
  const apiKey = process.env.REACT_APP_YOUTUBE_API_KEY;
  const url = `https://www.googleapis.com/youtube/v3/search?part=snippet&q=${encodeURIComponent(query)}&key=${apiKey}`;
  const res = await fetch(url);
  return (await res.json()).items;
}

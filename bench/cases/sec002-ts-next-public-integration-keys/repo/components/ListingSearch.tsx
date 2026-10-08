"use client";

import { liteClient as algoliasearch } from "algoliasearch/lite";
import posthog from "posthog-js";
import ReCAPTCHA from "react-google-recaptcha";
import { GoogleMap, useJsApiLoader } from "@react-google-maps/api";

posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY!, {
  api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST,
});

const search = algoliasearch(
  process.env.NEXT_PUBLIC_ALGOLIA_APP_ID!,
  process.env.NEXT_PUBLIC_ALGOLIA_SEARCH_API_KEY!,
);

export function ListingSearch() {
  const { isLoaded } = useJsApiLoader({
    googleMapsApiKey: process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY!,
  });
  return (
    <div>
      <p>Questions? Email {process.env.NEXT_PUBLIC_ADMIN_EMAIL}</p>
      {isLoaded && <GoogleMap zoom={12} center={{ lat: 47.6, lng: -122.3 }} />}
      <ReCAPTCHA sitekey={process.env.NEXT_PUBLIC_RECAPTCHA_SITE_KEY!} />
      <div data-search={String(Boolean(search))} data-mapbox={process.env.NEXT_PUBLIC_MAPBOX_TOKEN} />
    </div>
  );
}

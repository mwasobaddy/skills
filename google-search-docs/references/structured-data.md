# Structured data and rich results

Source: `search/docs/appearance/structured-data/**`.

## What structured data does and doesn't do

It makes a page **eligible** for enhanced appearance. It is not a ranking factor:

> "If your page contains a structured data issue, it can result in a manual action. A structured data
> manual action means that a page loses eligibility for appearance as a rich result; it doesn't affect
> how the page ranks in Google web search."

> "Using structured data enables a feature to be present, it does not guarantee that it will be present."

> "Google does not guarantee that your structured data will show up in search results, even if your page
> is marked up correctly according to the Rich Results Test."

Rich result ranking is separate from web ranking: "Rich result ranking takes extra information into
consideration" — and the more recommended properties supplied, the higher quality the result is to users.

## General guidelines

Eligibility requires compliance with **all three**: the Search content/anti-spam policies, the general
guidelines below, and the specific feature's own guide.

### Technical

- **Format:** JSON-LD (recommended), Microdata, or RDFa. JSON-LD is the default choice.
- **Access:** "Don't block your structured data pages to Googlebot using robots.txt, `noindex`, or any
  other access control methods."
- **Location:** "Put the structured data on the page that it describes, unless specified otherwise by the
  documentation."
- **Duplicates:** "If you have duplicate pages for the same content, we recommend placing the same
  structured data on all page duplicates, not just on the canonical page."
- **Required properties:** "Items that are missing required properties are not eligible for rich results."
- **Image URLs** in structured data "must be crawlable and indexable. Otherwise, Google Search can't find
  and display" them.
- Validate with the Rich Results Test and URL Inspection, which "catch most technical errors".

### Quality (not machine-testable)

- "Provide up-to-date information. We won't show a rich result for time-sensitive content that is no
  longer relevant."
- "Provide original content that you or your users have generated."
- "Don't mark up content that is not visible to readers of the page." If the JSON-LD describes a performer,
  the HTML body must describe that same performer.
- "Don't mark up irrelevant or misleading content, such as fake reviews or content unrelated to the focus
  of a page."
- "Don't use structured data to deceive or mislead users. Don't impersonate any person or organization, or
  misrepresent your ownership, affiliation, or primary purpose."
- Reviews and ratings not by actual users "may result in manual action".

## Live feature inventory

Required properties below were extracted from each feature page's own required-properties table. Pages
that document several types (video → `VideoObject`, `BroadcastEvent`, `Clip`, `SeekToAction`) list
separate requirements per type; only the primary type is shown.

| Feature page | Primary type | Required properties |
| --- | --- | --- |
| `article` | Article | *(none — all recommended)* |
| `book` | Book | `dataFeedElement`, `dateModified` |
| `breadcrumb` | BreadcrumbList | `itemListElement` |
| `carousel` | ItemList | `itemListElement` |
| `carousels-beta` | ItemList | `itemListElement`, `image`, `name`, `url` |
| `course` | Course | `description`, `name` |
| `dataset` | Dataset | `description`, `name` |
| `discussion-forum` | DiscussionForumPosting | *(see page)* |
| `education-qa` | Q&A | `hasPart`, `acceptedAnswer`, `eduQuestionType`, `text` |
| `employer-rating` | EmployerAggregateRating | `itemReviewed`, `ratingCount`, `ratingValue` |
| `event` | Event | `startDate` |
| `factcheck` | ClaimReview | `claimReviewed`, `reviewRating`, `url` |
| `image-license-metadata` | ImageObject | `contentUrl` |
| `job-posting` | JobPosting | `datePosted`, `description`, `hiringOrganization`, `jobLocation`, `title` |
| `local-business` | LocalBusiness | `address`, `name`, `image` |
| `loyalty-program` | MemberProgram | `description`, `hasTiers`, `name` |
| `math-solvers` | MathSolver | `potentialAction` |
| `merchant-listing` | Product | `name`, `image`, `offers`, `encoding` |
| `movie` | Movie | `image`, `name` |
| `organization` | Organization | *(none — all recommended)* |
| `product-snippet` | Product | `name` |
| `product-variants` | ProductGroup | `name` |
| `profile-page` | ProfilePage | *(none)* |
| `recipe` | Recipe | `name` |
| `return-policy` | MerchantReturnPolicy | `applicableCountry`, `returnPolicyCategory`, `merchantReturnLink`, `returnPolicySeasonalOverride` |
| `review-snippet` | Review | `author` |
| `shipping-policy` | ShippingService | `shippingConditions` |
| `speakable` | SpeakableSpecification | `cssSelector`, `xPath` |
| `video` | VideoObject | `name`, `thumbnailUrl`, `uploadDate` |

`product`, `vacation-rental`, `qapage`, `software-app`, and `paywalled-content` are overview pages that
delegate requirements to more specific guides.

Note that required lists are deliberately short. `Recipe` requires only `name`; `Event` only `startDate`.
Agencies routinely invent mandatory fields that Google does not require. The recommended properties are
what improve appearance, and they're listed on each feature page.

## Common combinations

| Page type | Types to use |
| --- | --- |
| Editorial / blog | `Article` or `BlogPosting` (+ `BreadcrumbList`) |
| Home page | `WebSite` (site name), `Organization` (logo, contact) |
| Product detail | `Product` + `Offer` (+ `AggregateRating`, `Review`) |
| Category / listing | `ItemList`, or `ProductGroup` for variants |
| Local business | `LocalBusiness` subtype |
| Video | `VideoObject` (+ `Clip` for key moments, `BroadcastEvent` for live) |
| Event | `Event` (never a past date for a byline) |
| FAQ content | **No `FAQPage` rich result exists any more** — see below |

## Retired features — do not implement

The following structured data types no longer produce rich results. Their documentation pages now redirect
to the "Latest documentation updates" page. Most SEO content still recommends them.

`FAQPage` · `HowTo` · `CourseInfo` · `CriticReview` · `EstimatedSalary` · `HomeActivities` ·
`JobTraining` · `LearningVideo` · `PracticeProblems` · `SitelinksSearchBox` · `SpecialAnnouncement` ·
`VehicleListing`

Also retired or absorbed: `Logo` (folded into `Organization`), the sitelinks search box feature, signed
exchanges, Web Light, and AMP-specific caching.

Before implementing any older guide, confirm the feature page still exists. A `301` to
`/search/updates` means the feature is gone.

## Structured data with JavaScript

Generating JSON-LD client-side is supported — Google renders pages before extracting markup — but the
rules that bite:

- The markup must be in the **rendered** output. Check with URL Inspection's rendered HTML.
- Don't block the script that produces it.
- Don't place it inside `data-nosnippet` elements expecting exclusion — structured data inside
  `data-nosnippet` "remains usable".
- Robots meta does not limit structured data use, except for creative-work `description` values such as
  `article.description`.

Prefer server-rendered JSON-LD. It removes an entire class of "works in the test, not in Search" failures.

## Implementation checklist

1. Pick the type from the live inventory above — confirm the page still exists.
2. Include every required property, then the recommended ones that genuinely describe the content.
3. Mark up only content that is visible on the page.
4. Put the markup on the page it describes, and on duplicate URLs too.
5. Ensure the page is crawlable and indexable.
6. Validate with the Rich Results Test; confirm rendered extraction with URL Inspection.
7. Watch the Manual Actions report — a structured-data action removes rich-result eligibility only.

"""Explicit one-time source for the P2-38 contrast candidate; no training code."""

import json
from pathlib import Path

GROUPS = []


def add(language, request, rule, constraints, entries):
    """Entries are subject|unique-role|constraint values, separated by semicolons."""
    GROUPS.append((language, request, rule, constraints, [part.split("|") for part in entries.split(";")]))


# HTML groups: semantic destination, native control, label, and value contrasts.
add("html", "Create a semantic {0} navigation region with an accessible {0} label.", "navigation", "element:semantic-element:nav,attribute:aria-label:{0}", "Support|support-links-region|Support;Legal|legal-links-region|Legal;Account|account-links-region|Account")
add("html", "Create a visibly labeled required {0} contact control using the native {1} input type.", "contact", "element:input-type:{1},attribute:required:true,behavior:label-association:required", "email address|contact-email-entry|email;telephone number|contact-telephone-entry|tel;postal code|contact-postal-entry|text")
add("html", "Create an announced status message that says {1} for the {0} workflow.", "status", "attribute:role:status,text:message:{1}", "upload|upload-progress-announcement|Upload in progress;sync|sync-progress-announcement|Sync in progress;import|import-progress-announcement|Import in progress")
add("html", "Create a native disclosure for {0} policy details with a visible {0} summary.", "disclosure", "element:container:details,element:label-element:summary,text:label:{0}", "Returns|returns-policy-details|Returns;Warranty|warranty-policy-details|Warranty;Pickup|pickup-policy-details|Pickup")
add("html", "Create a captioned {0} table with column-scoped headings.", "table", "element:container:table,text:caption:{0},attribute:header-scope:col", "Inventory|inventory-stock-table|Inventory;Schedule|schedule-times-table|Schedule;Pricing|pricing-tiers-table|Pricing")
add("html", "Create a fieldset for choosing one {0} option with a {0} legend and labeled radio controls.", "radio", "element:group:fieldset,element:group-label:legend,text:legend:{0},element:control-type:radio", "Delivery|delivery-choice-fieldset|Delivery;Color|color-choice-fieldset|Color;Plan|subscription-choice-fieldset|Plan")
add("html", "Create a {0} figure with a descriptive figcaption about {0}.", "figure", "element:container:figure,element:caption:figcaption,text:caption-topic:{0}", "Product photo|product-photo-figure|Product photo;Location map|location-map-figure|Location map;Sales chart|sales-chart-figure|Sales chart")
add("html", "Create a labeled {0} form control using native input type {1}.", "form", "element:input-type:{1},text:label:{0},behavior:label-association:required", "Website URL|website-url-input-control|url;Quantity|quantity-number-input-control|number;Birth date|birthdate-input-control|date")
add("html", "Create a semantic section for {0} with a visible {0} heading.", "section", "element:semantic-element:section,text:heading:{0}", "Help|help-content-landmark|Help;Billing|billing-content-landmark|Billing;Security|security-content-landmark|Security")
add("html", "Create a native button labeled {0} with type {1}.", "button", "element:semantic-element:button,attribute:type:{1},text:label:{0}", "Search|search-submit-control|submit;Reset filters|filter-reset-control|reset;Preview|preview-open-control|button")
add("html", "Create a {0} progress element with current value {1} of maximum 100.", "progress", "element:semantic-element:progress,attribute:value:{1},attribute:max:100", "Download|download-quarter-progress|25;Export|export-half-progress|50;Backup|backup-threequarter-progress|75")
add("html", "Create a semantic {0} list with {1} as its container and {2} as its item element.", "list", "element:container:{1},element:item:{2},text:topic:{0}", "Setup steps|setup-steps-list|ol|li;Feature bullets|features-bullet-list|ul|li;Glossary terms|glossary-definition-list|dl|dt")

# CSS groups: concrete styling values vary with the component or state.
add("css", "Modify the {0} as a flex row with a {1} gap.", "flex", "declaration:display:flex,declaration:gap:{1}", "action strip|action-strip-flex-gap|0.75rem;metadata line|metadata-line-flex-gap|0.25rem;filter row|filter-row-flex-gap|1.25rem")
add("css", "Modify the {0} into a three-column grid with a {1} gap.", "grid", "declaration:display:grid,declaration:grid-template-columns:repeat(3/ 1fr),declaration:gap:{1}", "dashboard tiles|dashboard-tiles-grid|12px;report cards|report-cards-grid|20px;profile panels|profile-panels-grid|8px")
add("css", "Modify {0} focus-visible styling to use a {1} outline and a {2} offset.", "focus", "state:interaction-state:focus-visible,declaration:outline:{1},declaration:outline-offset:{2}", "link|link-focus-outline|2px solid currentColor|2px;input|input-focus-outline|2px solid blue|3px;tab|tab-focus-outline|3px solid orange|1px")
add("css", "Modify the {0} to stay sticky at top offset {1}.", "sticky", "declaration:position:sticky,declaration:top:{1}", "subnavigation|subnavigation-sticky-offset|48px;filter controls|filter-controls-sticky-offset|64px;summary bar|summary-bar-sticky-offset|80px")
add("css", "Modify the {0} so its {1} state displays the panel as {2}.", "state", "state:data-state:{1},relationship:target:{0},declaration:display:{2}", "drawer|open-drawer-visibility|open|block;tooltip|closed-tooltip-visibility|closed|none;menu|open-menu-visibility|open|flex")
add("css", "Modify the {0} to wrap as a flex row with a {1} gap.", "wrap", "declaration:display:flex,declaration:flex-wrap:wrap,declaration:gap:{1}", "tag row|tag-row-wrapping|4px;button row|button-row-wrapping|8px;chip row|chip-row-wrapping|12px")
add("css", "Modify the {0} component to have {1} internal padding.", "padding", "declaration:padding:{1}", "alert box|alert-box-padding|0.75rem;dialog body|dialog-body-padding|1.5rem;notice banner|notice-banner-padding|1rem")
add("css", "Modify print styling so {0} is hidden on paper.", "print", "state:media:print,relationship:target:{0},declaration:display:none", "interactive controls|print-controls-hidden;video player|print-video-hidden;live chat widget|print-chat-hidden")
add("css", "Modify the {0} text to truncate to one line with an ellipsis at width {1}.", "ellipsis", "declaration:max-width:{1},declaration:white-space:nowrap,declaration:text-overflow:ellipsis,declaration:overflow:hidden", "file title|file-title-truncation|12rem;author name|author-name-truncation|9rem;project label|project-label-truncation|15rem")
add("css", "Modify the disabled {0} to have opacity {1} and ignore pointer events.", "disabled", "state:interaction-state:disabled,declaration:opacity:{1},declaration:pointer-events:none", "save control|disabled-save-opacity|0.5;download control|disabled-download-opacity|0.35;submit control|disabled-submit-opacity|0.6")
add("css", "Modify reduced-motion styling for the {0} animation to duration {1}.", "reduced motion", "state:media:prefers-reduced-motion reduce,declaration:animation-duration:{1}", "loading pulse|loading-pulse-reduced-motion|0.01ms;toast slide|toast-slide-reduced-motion|0.02ms;skeleton shimmer|skeleton-shimmer-reduced-motion|0.03ms")
add("css", "Modify the {0} to be a {1} square using border-box sizing.", "size", "declaration:width:{1},declaration:height:{1},declaration:box-sizing:border-box", "avatar|avatar-square-size|40px;thumbnail|thumbnail-square-size|72px;icon tile|icon-tile-square-size|56px")

# JavaScript groups: key, bounds, locale, policy, and transformation contrasts.
add("javascript", "Create a helper that clamps {0} inclusively between {1} and {2}.", "bound", "behavior:lower-bound:{1},behavior:upper-bound:{2},behavior:inclusive:true", "percentage|percentage-bounds-helper|0|100;rating|rating-bounds-helper|1|5;volume|volume-bounds-helper|0|10")
add("javascript", "Create a helper that keeps the first item for each {0} and preserves input order.", "unique", "behavior:dedupe-key:{0},behavior:duplicate-policy:keep-first,behavior:order:preserve-input", "email|unique-email-records;slug|unique-slug-records;code|unique-code-records")
add("javascript", "Create a helper that formats a number as {0} currency for locale {1}.", "currency", "api:formatter:Intl.NumberFormat,behavior:locale:{1},behavior:currency:{0}", "EUR|eur-german-currency|de-DE;GBP|gbp-british-currency|en-GB;CAD|cad-canadian-currency|en-CA")
add("javascript", "Create a nonmutating helper that toggles {0} membership, removing when present and appending when absent.", "toggle", "behavior:membership-key:{1},behavior:present-case:remove-target,behavior:absent-case:append-target,nonmutation:input-array:preserve", "favorite product codes|toggle-favorite-code-membership|product-code;selected tag names|toggle-selected-tag-membership|tag-name;blocked user handles|toggle-blocked-handle-membership|user-handle")
add("javascript", "Create a helper that computes the {0} of finite numeric {1} values, ignoring missing values.", "aggregate", "behavior:aggregation:{0},behavior:property:{1},behavior:invalid-values:ignore", "average|average-score-values|score;maximum|maximum-price-values|price;minimum|minimum-duration-values|duration")
add("javascript", "Create a nonmutating helper that orders items by {0} using locale-aware comparison.", "sort", "behavior:sort-key:{0},api:comparison:localeCompare,nonmutation:input-array:preserve", "title|order-items-by-title;city|order-items-by-city;category|order-items-by-category")
add("javascript", "Create a helper that parses {0} with {1}, returning null for invalid input.", "parse", "api:parser:{1},behavior:format:{2},behavior:invalid-result:null", "base-10 integers|parse-decimal-integer-input|Number.parseInt|radix-10;JSON objects|parse-json-object-input|JSON.parse|object-only;ISO dates|parse-iso-date-input|Date.parse|ISO-8601")
add("javascript", "Create a helper that indexes items by {0}, keeping the last item for a repeated key.", "index", "behavior:index-key:{0},behavior:duplicate-policy:keep-last", "email|index-records-by-email;slug|index-records-by-slug;code|index-records-by-code")
add("javascript", "Create a nonmutating helper that divides an array into {0} of {1}, allowing a shorter last group.", "group", "behavior:group-size:{1},behavior:last-group:allow-short,nonmutation:input-array:preserve", "chunks|chunk-items-into-fours|4;batches|batch-items-into-eights|8;pages|page-items-into-twelves|12")
add("javascript", "Create a helper that {0} calls with a {1}ms delay.", "timing", "behavior:timing-mode:{2},behavior:delay-ms:{1}", "debounces search|debounce-search-calls|250|debounce;throttles scroll|throttle-scroll-calls|100|throttle;debounces resize|debounce-resize-calls|400|debounce")
add("javascript", "Create a nonmutating helper that {0} from an input array.", "transform", "behavior:transformation:{1},behavior:selection:{2},nonmutation:input-array:preserve", "flattens one level|flatten-one-level-items|flatten|depth-one;removes nullish entries|compact-nullish-items|filter|exclude-null-undefined;selects active entries|select-active-items|filter|active-true")
add("javascript", "Create a helper that groups records by their {0} property into arrays.", "group by", "behavior:group-key:{0},behavior:group-values:arrays", "type|group-records-by-type;status|group-records-by-status;category|group-records-by-category")


def main():
    rows = []
    tags = {"html": "html", "css": "css", "javascript": "js"}
    kinds = {"html": "html-element", "css": "css-rule", "javascript": "js-function"}
    per_language = {language: 0 for language in tags}
    for language, template, family, specs, entries in GROUPS:
        per_language[language] += 1
        group_number = per_language[language]
        group_id = f"p238-{tags[language]}-g{group_number:02d}"
        assert len(entries) == 3
        for number, entry in enumerate(entries, 1):
            subject, role, *extra = entry
            values = [subject, *extra]
            constraints = []
            for spec in specs.split(","):
                kind, key, value = spec.split(":", 2)
                constraints.append({"kind": kind, "key": key, "value": value.format(*values).replace("/", ",")})
            request = template.format(*values)
            action = "modify" if language == "css" else "create"
            plan = {"schemaVersion": 1, "language": language, "action": action,
                    "targetKind": kinds[language], "targetRole": role, "constraints": constraints,
                    "searchHints": [subject, family]}
            rows.append({"schemaVersion": 1, "id": f"{group_id}-{number:02d}",
                         "candidateSplit": "train" if group_number <= 8 else "validation",
                         "contrastGroupId": group_id, "language": language,
                         "provenance": "project-authored-p2-38-semantic-binding-candidate",
                         "approvalStatus": "pending-owner-review", "request": request,
                         "solution": json.dumps(plan, separators=(",", ":")),
                         "targetRole": role, "targetKind": kinds[language], "action": action})
    assert per_language == {language: 12 for language in tags}
    assert len(rows) == 108
    output = Path(__file__).with_name("p2-38-semantic-binding-candidate-v1.jsonl")
    output.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()

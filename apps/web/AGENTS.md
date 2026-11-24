<!-- LOVABLE:BEGIN -->
> [!IMPORTANT]
> This project is connected to [Lovable](https://lovable.dev). Avoid rewriting
> published git history — force pushing, or rebasing/amending/squashing commits
> that are already pushed — as it rewrites history on Lovable's side and the
> user will likely lose their project history.
>
> Commits you push to the connected branch sync back to Lovable and show up in
> the editor, so keep the branch in a working state.
<!-- LOVABLE:END -->

- Chapter 1 uses RiseOnScroll to measure a stationary outer wrapper and transform only its inner vignette, preventing scroll-measurement feedback.
- Declare canonical and structured site metadata on the home leaf route; keep social image tags off the root to avoid overriding page previews.
- Gate the decorative hero canvas until after mount so reduced-motion and mobile preferences cannot change the server/client markup during hydration.
- Wrap the three home story vignettes in MotionPause; CSS animations and JavaScript clocks honor its shared pause class so the user controls looping motion.
- Keep illustrative home-example values separate from live dataset ranking and share them between chat and report, so the public story remains consistent without changing real recommendations.
- Use the shared scroll-reveal hook and timing policy for home entrances: visible SSR markup, JS-only pending styles, one-shot viewport observation, and immediate hash destinations prevent unreadable gaps.
- Centralize keyboard outlines and readable brand text in semantic CSS tokens; mark dark-surface controls with the inverse-focus class so component resets cannot hide focus.
- The guided-choice route owns question focus and announcements; StepStage must not run competing scroll timers so each answer lands on the next heading.
- Carry home requests in validated q search state with a legacy storage fallback; infer only explicit values through wizard-input and skip corresponding answered questions.
- Apply the same accent/case-insensitive text inference to home requests and submitted free text, preserving explicit button answers; infer experience from explicit driving (at least two years when numbered) or same-type ownership, leaving conflicting or negated declarations unanswered.
- Translate category labels at presentation boundaries through category-labels; keep dataset values unchanged for matching and ranking.
- Compute wizard completion only after questions load, and render answered questions in answer insertion order before the active question; consumed home text stays exclusively in its initial message.
- Keep contact validation and reason-specific payload filtering shared between browser and server; save requests privately with database rate limiting, show receipts only after persistence, and never attach technical or analysis data without explicit opt-in.
- Share home FAQ data with contact suggestions; use same-origin pathname-only provenance and owner-scoped saved-analysis reads, with opt-in home navigation on the legal layout to leave other legal pages unchanged.
- ContactForm owns the contact split layout, live receipt rows and blur-validated data flights; only confirmed persistence triggers the CSS stamp with the saved code before the final receipt, and reduced motion skips the confirmation delay. Share ticket rows and email masking between desktop and compact mobile previews; announce validated values rather than keystrokes.

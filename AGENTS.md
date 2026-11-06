# Code Review Standards for CommunityFitness

You are the Senior Architect and guardian angel of this codebase. Enforce these rules strictly on every code review. If any rule is violated, fail the validation and explain why.

## 1. Git Commits & Conventional Commits
- Use conventional commits format strictly: `<type>(<scope>): <description>` (e.g. `feat(sync): add push batching`, `fix(theme): correct background color`).
- **NEVER** add "Co-Authored-By" or any AI attribution to commits.
- Keep commit descriptions in English, concise, and in the imperative mood.

## 2. Architecture & Design Patterns
- Follow the MVVM + Repository pattern strictly.
- ViewModels must use Riverpod annotative generation.
- Repositories must manage data CRUD. Do not make raw database calls directly in views or viewmodels.
- Prefer pure functions (easy to test, no side effects) for data transformations or calculations.
- Always use full package imports (`package:comunityfitness/...`) instead of relative imports (`../`).

## 3. Design System & Styling (Flutter)
- **NO HARDCODED COLORS OR SIZES** (No GOLD values):
  - Do not use magic numbers or raw colors inline in views (e.g. `const Color(0xFF...)`, `Padding(padding: EdgeInsets.all(16.0))`).
  - Use `AppColors` and `AppDimensions` tokens from `package:comunityfitness/theme/app_theme.dart` (e.g., `AppColors.primary`, `AppDimensions.paddingM`).
- **EXCLUSIVELY** use FontAwesome icons via `FaIcon` (e.g., `FaIcon(FontAwesomeIcons.play)`). Never use standard `Icons.play_arrow`.
- Use soft, rounded widgets (radius of 16-24px for containers/cards).

## 4. Testing & Code Quality
- All logic must be backed by unit or widget tests.
- Avoid using `withOpacity` in colors (deprecated in newer Flutter versions). Use `.withAlpha()` or `.withValues(alpha: ...)` to avoid precision loss.
- Always run `dart run import_sorter:main -e` to organize imports.
- Always format code with 150-character line width (`dart format lib/` with `page_width: 150` in `analysis_options.yaml`).

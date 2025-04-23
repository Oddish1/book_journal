# Book Journal

This is being developed for my capstone project.

## Currently in Progress

- [X] Email integration for password reset
  - [X] noreply email setup
  - [X] welcome template
  - [X] password reset
  - [X] email verification?
- [X] Public user profiles
  - [X] User profile editing page with image upload/optimization
  - [X] public user profile page
  - [X] populate user links on all pages publicly referencing users (reviews, journals, etc.)
  - [X] User following + email alerts
- [ ] Public journals aggregate page on book page
- [ ] Currently reading count on book page
- [ ] Num. finished reading on book page
- [X] User search & finish search styling
- [ ] Journal filtering (keyword search, user-set tags)
- [ ] Refine/Unify Styling
  - [ ] public profile page
- [ ] Auto-tagging system (sentiment analysis + keyword extraction)
  - [ ] Reviews
  - [ ] Journals
  - [ ] Books (descriptions)

## Development Backlog

- [X] Move to PostreSQL db

## Finished

- [X] Search
- [X] Optimize database transactions
- [X] Recommendations
  - [X] Set finished in journal entry
  - [X] Prompt user for reviews if finished and not reviewed
  - [X] Review form + storage
  - [X] Recommendation Algorithm
  - [X] Add ratings to books on db for easier lookup
  - [X] Show Reviews on book page
  - [X] Show User reviews on library page
  - [X] Generate recommendations when user submits new review
- [X] UI Tweaking (remove cards, remove book titles, simplify display)
  - [X] Homepage
  - [X] Book Page
    - [X] split in thirds only book details scroll -> book image | book details | list functionality)
    - [X] review aggregation link
  - [X] Library Page
  - [X] Login Page
  - [X] Register Page
  - [X] Journal Page
    - [X] Journal Home
    - [X] Individual Journal Pages
    - [X] Pages that link to journals need individual journal links
    - [X] New Journals
    - [X] New Reviews
  - [X] About Page

- [X] Individual Review pages for full review
- [X] Add link on review count on book page leading to aggregated reviews for that book
- [X] API Integration
  - [X] Fetch book details
- [X] Implement Books
  - [X] Auto-Add Books from API to DB
  - [X] Book Details Page
- [X] Implement Journal
  - [X] Journal Page (sort by timestamp)
  - [X] New Journal Page
  - [X] Journals on book page
- [X] Implement Lists
  - [X] Adding Book to List
    - [X] Book Page
  - [X] Removing Book from List
    - [X] Book Page
- [X] Library Page
  - [X] styling
  - [X] currently reading (w/ link to new journal for the book)
  - [X] user's lists
  - [X] latest journals (10)
- [X] Data Models
- [X] Authentication
  - [X] Registration
  - [X] Login
  - [X] Logout

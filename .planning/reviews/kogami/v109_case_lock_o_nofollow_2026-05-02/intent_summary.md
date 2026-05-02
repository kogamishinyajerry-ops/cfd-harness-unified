roadmap_milestone: M7.1
business_goal: Close the documented symlink-swap residual on the case_lock primitive so a swapped case directory can no longer redirect lockfile creation to an arbitrary target outside the case root.
affected_subsystems:
  - case_lock shared primitive
  - patch_classification override store
  - setup_bc dispatcher
  - raw_dict editor route
rationale: The lockfile path is already symlink-protected but the case directory itself is opened by name, so a swapped or planted case-dir symlink redirects the lockfile creation path. Adding an O_NOFOLLOW O_DIRECTORY open of the case directory before the lockfile open closes the threat for every caller of case_lock at once, replacing the per-caller defensive checks each downstream module has had to grow.

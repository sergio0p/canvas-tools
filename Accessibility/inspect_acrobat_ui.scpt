-- Diagnostic script to inspect Acrobat UI elements
-- Usage: osascript inspect_acrobat_ui.scpt "/path/to/test.pdf"
-- Output: Creates acrobat_ui_dump.txt in same directory as this script

on run argv
	if (count of argv) < 1 then
		return "ERROR: Please provide a PDF path"
	end if

	set pdfPath to item 1 of argv
	set pdfFile to POSIX file pdfPath

	-- Prepare output file
	set scriptPath to POSIX path of ((path to me as text) & "::")
	set outputFile to scriptPath & "acrobat_ui_dump.txt"
	set output to ""

	-- Open PDF in Acrobat
	tell application "Adobe Acrobat"
		activate
		open pdfFile
		delay 3
	end tell

	-- Inspect UI elements
	tell application "System Events"
		tell process "Acrobat"
			-- Get basic window info
			set windowCount to count of windows
			set output to output & "Number of windows: " & windowCount & return & return

			-- Check for Tools menu
			set output to output & "=== CHECKING FOR TOOLS MENU ===" & return
			try
				tell menu bar 1
					set menuNames to name of every menu bar item
					set output to output & "Menu bar items: " & menuNames & return & return

					-- Check if Tools menu exists
					try
						tell menu bar item "Tools"
							set output to output & "✓ Tools menu found" & return
							set toolsMenuItems to name of menu items of menu "Tools"
							set output to output & "Tools menu items: " & toolsMenuItems & return & return
						end tell
					on error
						set output to output & "✗ Tools menu not found in menu bar" & return & return
					end try
				end tell
			end try

			-- Inspect first window if exists
			if windowCount > 0 then
				set output to output & "=== WINDOW 1 DETAILS ===" & return
				tell window 1
					set output to output & "Window name: " & name & return
					set output to output & "Window role: " & role & return & return

					-- List buttons
					set output to output & "=== BUTTONS ===" & return
					try
						repeat with btn in buttons
							try
								set btnInfo to "Button: " & (name of btn) & " | Description: " & (description of btn)
								set output to output & btnInfo & return
							end try
						end repeat
					end try
					set output to output & return

					-- List groups
					set output to output & "=== GROUPS ===" & return
					try
						set groupCount to count of groups
						set output to output & "Number of groups: " & groupCount & return
						repeat with i from 1 to groupCount
							try
								set grp to group i
								set grpInfo to "Group " & i & ": " & (description of grp)
								set output to output & grpInfo & return

								-- List buttons in this group
								try
									repeat with btn in buttons of grp
										try
											set btnInfo to "  └─ Button: " & (name of btn)
											set output to output & btnInfo & return
										end try
									end repeat
								end try
							end try
						end repeat
					end try
					set output to output & return

					-- List toolbars
					set output to output & "=== TOOLBARS ===" & return
					try
						repeat with tb in toolbars
							try
								set tbInfo to "Toolbar: " & (description of tb)
								set output to output & tbInfo & return
							end try
						end repeat
					end try
				end tell
			end if
		end tell
	end tell

	-- Write to file
	try
		set fileHandle to open for access (POSIX file outputFile) with write permission
		set eof of fileHandle to 0
		write output to fileHandle
		close access fileHandle
	on error
		try
			close access (POSIX file outputFile)
		end try
	end try

	-- Close Acrobat
	tell application "Adobe Acrobat"
		close active doc saving no
	end tell

	return "UI inspection complete! Output saved to: " & outputFile
end run

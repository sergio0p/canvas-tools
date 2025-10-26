-- AppleScript for Auto-Tagging PDFs in Adobe Acrobat Pro 2020
-- Usage: osascript tag_pdf_acrobat.scpt "/path/to/file.pdf" wait_seconds

on run argv
	if (count of argv) < 2 then
		return "ERROR: Missing arguments. Usage: osascript tag_pdf_acrobat.scpt <pdf_path> <wait_seconds>"
	end if

	set pdfPath to item 1 of argv
	set waitSeconds to item 2 of argv as number

	-- Verify PDF exists
	set pdfFile to POSIX file pdfPath
	tell application "System Events"
		if not (exists file pdfPath) then
			return "ERROR: PDF file not found: " & pdfPath
		end if
	end tell

	try
		-- Close all Acrobat documents to start fresh
		tell application "Adobe Acrobat"
			try
				close every document saving no
			end try
			delay 0.5
		end tell

		-- Open PDF in Acrobat Pro 2020
		tell application "Adobe Acrobat"
			activate
			open pdfFile
			delay 3 -- Wait for document to load completely
		end tell

		-- Access Accessibility Autotag via menu (most reliable method)
		tell application "System Events"
			tell process "Acrobat"
				-- Method 1: Try direct menu access (Tools → Accessibility → Autotag Document)
				try
					click menu bar item "Tools" of menu bar 1
					delay 0.5
					click menu item "Accessibility" of menu "Tools" of menu bar item "Tools" of menu bar 1
					delay 0.5
					click menu item "Autotag Document" of menu "Accessibility" of menu "Tools" of menu bar item "Tools" of menu bar 1
					delay 1

					-- Success via menu
					set menuSuccess to true
				on error errMsg1
					-- Menu method failed, try UI method
					set menuSuccess to false
				end try

				-- Method 2: If menu failed, try UI element method
				if not menuSuccess then
					-- Show Tools panel if not visible
					try
						click menu bar item "View" of menu bar 1
						delay 0.3
						click menu item "Tools" of menu "View" of menu bar item "View" of menu bar 1
						delay 1.5
					end try

					-- Look for Accessibility tool and click "Open" button
					set foundAccessibility to false

					-- Try to find the Accessibility "Open" button
					repeat with i from 1 to 20
						try
							-- Look for a button with "Open" that's near Accessibility
							set allButtons to buttons of window 1
							repeat with btn in allButtons
								try
									if (name of btn is "Open" or description of btn contains "Open") then
										-- Click it and see if it's the Accessibility one
										click btn
										delay 1
										set foundAccessibility to true
										exit repeat
									end if
								end try
							end repeat

							if foundAccessibility then
								exit repeat
							end if
						end try
						delay 0.2
					end repeat

					if not foundAccessibility then
						return "ERROR: Could not find Accessibility tool. Please ensure it's available in Tools panel."
					end if

					-- Now look for "Autotag Document" button
					delay 1
					try
						click button "Autotag Document" of window 1
						delay 1
					on error
						return "ERROR: Found Accessibility tool but could not find Autotag Document button"
					end try
				end if

				-- Handle any dialogs that might appear (reading order, etc.)
				delay 2

				-- Check for dialog boxes and click OK/Continue/Recommended option
				repeat 3 times
					try
						-- Try to find and click common dialog buttons
						if exists button "OK" of window 1 then
							click button "OK" of window 1
							delay 0.5
						else if exists button "Continue" of window 1 then
							click button "Continue" of window 1
							delay 0.5
						else if exists button "Start" of window 1 then
							click button "Start" of window 1
							delay 0.5
						end if
					end try
					delay 0.5
				end repeat
			end tell
		end tell

		-- Wait for auto-tagging to complete
		delay waitSeconds

		-- Save the document (overwrite original)
		tell application "System Events"
			tell process "Acrobat"
				-- Use Command+S to save
				keystroke "s" using command down
				delay 2

				-- Handle any save dialogs
				repeat 3 times
					try
						if exists button "Save" of window 1 then
							click button "Save" of window 1
							delay 0.5
						else if exists button "Replace" of window 1 then
							click button "Replace" of window 1
							delay 0.5
						else if exists button "OK" of window 1 then
							click button "OK" of window 1
							delay 0.5
						end if
					end try
					delay 0.3
				end repeat
			end tell
		end tell

		-- Close the document
		delay 1
		tell application "Adobe Acrobat"
			try
				close active doc saving no
			end try
			delay 0.5
		end tell

		return "SUCCESS: Tagged and saved " & pdfPath

	on error errMsg number errNum
		-- Try to close Acrobat gracefully on error
		try
			tell application "Adobe Acrobat"
				close every document saving no
			end tell
		end try

		return "ERROR: " & errMsg & " (Error " & errNum & ")"
	end try
end run

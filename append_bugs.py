NEW_BUGS = [
    # Machine Learning / AI
    ["ValueError: shapes (X, Y) and (Y, Z) not aligned: Y (dim 1) != Y (dim 0)", "Matrix multiplication dimension mismatch. In NumPy/PyTorch/TensorFlow, ensure the inner dimensions match for dot products. You might need to transpose one matrix using `.T` or `.transpose()`.", "Python, Data Science", "numpy pytorch tensor shape valueerror dimension matrix align"],
    ["OutOfMemoryError: GPU memory usage", "Your model or data is too large for the GPU. Decrease the `batch_size`, clear CUDA cache (`torch.cuda.empty_cache()`), use gradient accumulation, or enable mixed precision (`torch.autocast`).", "PyTorch, CUDA", "pytorch cuda gpu memory outofmemoryerror batch size"],
    ["ValueError: Input contains NaN, infinity or a value too large for dtype('float64').", "Your dataset has missing or infinite values. Use `df.fillna()` to impute missing values, or `df.dropna()` to remove them before feeding data to a scikit-learn model.", "scikit-learn, Pandas", "sklearn pandas nan missing values infinity float64 valueerror"],
    ["ModuleNotFoundError: No module named 'tensorflow'", "TensorFlow is not installed in the current environment. Run `pip install tensorflow` (or `pip install tensorflow-macos` on Apple Silicon). Make sure you're using the correct virtual environment.", "Python, TensorFlow", "python tensorflow module import error env"],
    
    # iOS / Swift
    ["Thread 1: signal SIGABRT", "Often caused by a disconnected IBOutlet or IBAction in a Storyboard/XIB. Check the Connections Inspector in Xcode for any yellow warnings indicating a missing connection, and delete the bad link.", "iOS, Swift, Xcode", "ios swift xcode sigabrt iboutlet storyboard connection"],
    ["Ambiguous reference to member 'X'", "The Swift compiler cannot figure out which overloaded function or type you mean. Provide more explicit type annotations, or fully qualify the module name (e.g. `Module.Class`).", "Swift", "swift compile error ambiguous reference member type"],
    ["Command PhaseScriptExecution failed with a nonzero exit code", "A build script (like CocoaPods or a custom bash script) failed. Check the build logs by clicking the Report Navigator in Xcode and looking at the details of the PhaseScriptExecution step.", "iOS, Xcode", "ios xcode build error phasescriptexecution script pod"],

    # Android / Kotlin
    ["Unresolved reference: synthetic", "Kotlin Android Extensions (`kotlinx.synthetic`) are deprecated and removed. Migrate to ViewBinding: enable `buildFeatures { viewBinding = true }` in `build.gradle` and use the generated binding classes.", "Android, Kotlin", "android kotlin synthetic deprecated viewbinding reference"],
    ["java.lang.SecurityException: Permission Denial", "You forgot to declare a required permission in `AndroidManifest.xml` (e.g., `<uses-permission android:name=\"android.permission.INTERNET\"/>`) or you didn't request it at runtime for dangerous permissions.", "Android, Java", "android permission securityexception manifest denial runtime"],
    ["Missing classes detected while running R8", "R8/ProGuard removed a class needed at runtime or via reflection. Add a `@Keep` annotation to the class or update your `proguard-rules.pro` with a `-keep` rule for that package.", "Android, ProGuard", "android r8 proguard keep missing class reflection"],

    # DevOps / CI CD
    ["Ansible: SSH Error: data could not be sent to remote host", "The SSH connection dropped or timed out. This can happen if a task restarts the network or SSH daemon. Use the `wait_for_connection` module or `async` tasks for long-running commands.", "Ansible", "ansible ssh timeout network restart connection error"],
    ["fatal: not a git repository (or any of the parent directories): .git", "You ran a git command in a directory that isn't a Git repository. Run `git init` or `cd` into the correct directory.", "Git", "git fatal repository directory missing .git init"],
    ["Your branch and 'origin/main' have diverged", "You and someone else both made commits to the same branch. You must reconcile them: `git pull --rebase origin main`.", "Git", "git branch diverged origin main pull rebase"],

    # DB / SQL
    ["ERROR 1452 (23000): Cannot add or update a child row: a foreign key constraint fails", "You tried to insert a row with a foreign key value that does not exist in the parent table. Insert the parent row first, or correct the foreign key ID.", "MySQL, MariaDB", "mysql 1452 foreign key constraint child row parent"],
    ["ORA-12154: TNS:could not resolve the connect identifier specified", "Oracle client cannot find the database alias in your `tnsnames.ora` file. Ensure the file is in your `TNS_ADMIN` path and the alias is spelled correctly.", "Oracle", "oracle ora-12154 tns resolve identifier connection"],
    ["SQLite: OperationalError: no such table: X", "The table doesn't exist. You either haven't run your migrations, you're pointing to an empty/new SQLite file by mistake, or there's a typo in the table name.", "SQLite", "sqlite operationalerror table missing database file"],

    # Web / Browser
    ["Refused to display 'X' in a frame because it set 'X-Frame-Options' to 'deny'.", "The site you are trying to put in an `<iframe>` explicitly blocks framing for security reasons (clickjacking protection). You cannot bypass this from the client side.", "Browser, HTML", "iframe security x-frame-options deny clickjacking html"],
    ["Uncaught (in promise) DOMException: play() failed because the user didn't interact with the document first.", "Autoplay of audio/video with sound is blocked by modern browsers until the user clicks or taps the page. Mute the video (`<video muted autoplay>`) or require a click to play.", "JavaScript, Browser", "javascript domexception play autoplay video audio interaction"],

    # GraphQL
    ["GraphQLError: Cannot query field \"X\" on type \"Y\".", "The field you requested in your GraphQL query does not exist in the schema for that type. Check the schema or introspection docs to find the correct field name.", "GraphQL", "graphql error query field missing schema type"],
    ["ApolloError: Response not successful: Received status code 400", "The GraphQL server rejected the query, usually because of a syntax error or validation failure. Check the network tab response body for the exact GraphQL error message.", "GraphQL, Apollo", "graphql apollo 400 response network error status"],

    # Java / Kotlin
    ["java.lang.UnsupportedClassVersionError: X has been compiled by a more recent version of the Java Runtime", "You compiled the code with a newer JDK (e.g. Java 17) but are trying to run it with an older JRE (e.g. Java 11). Upgrade your JRE or set your compiler target to an older version.", "Java", "java unsupportedclassversionerror jre jdk version compiler"],
    ["Kotlin: Val cannot be reassigned", "You declared a variable with `val` (immutable) and tried to change it. Use `var` if the variable needs to be mutable.", "Kotlin", "kotlin val reassigned var immutable mutable variable"],
    
    # Cloudflare / DNS
    ["Error 521: Web server is down", "Cloudflare can connect to your origin IP, but your web server (Nginx/Apache/App) is not listening on the expected port, or is actively refusing connections. Check your server's firewall and process.", "Cloudflare, Networking", "cloudflare 521 web server down proxy origin"],
    ["Error 522: Connection timed out", "Cloudflare couldn't establish a TCP connection to your origin server. Usually means the origin server's firewall (e.g. AWS Security Group) is blocking Cloudflare's IPs.", "Cloudflare, Networking", "cloudflare 522 timeout firewall security group proxy"],
    
    # Generic Backend
    ["Error: write EPIPE", "The client closed the TCP connection before the server finished sending the response. This is common when users cancel file downloads or navigate away from a page mid-request.", "Node.js, Networking", "node epipe write tcp socket connection closed broken pipe"],
    ["ERR_TOO_MANY_REDIRECTS", "Your server or proxy is stuck in a redirect loop. Commonly happens when Cloudflare is set to 'Flexible' SSL but your server redirects HTTP to HTTPS, causing an infinite loop. Change Cloudflare to 'Full (Strict)'.", "Networking, Cloudflare", "redirects loop err_too_many_redirects ssl flexible cloudflare"],

    # Webpack / Babel
    ["SyntaxError: Cannot use import statement outside a module (Babel)", "Babel didn't transpile the file. Ensure the file is covered by your Babel `include` paths, and that your `.babelrc` has `@babel/preset-env` configured.", "Babel, JavaScript", "babel syntaxerror import esm transpile preset-env"],
    ["Webpack: You may need an appropriate loader to handle this file type", "Webpack doesn't know how to parse the file (e.g., `.css`, `.vue`, `.png`). Install and configure the correct loader in your `webpack.config.js` (e.g., `css-loader`, `file-loader`).", "Webpack", "webpack loader file type parse error build"],
    
    # CSS Preprocessors
    ["SassError: Undefined variable.", "You're trying to use a Sass variable (e.g., `$primary-color`) without importing the file where it's defined. Add `@use 'path/to/variables';` at the top of the file.", "Sass, CSS", "sass scss error undefined variable import use"],

    # Shell Scripting
    ["syntax error: unexpected end of file", "You missed a closing keyword in your bash script. Check for a missing `fi` for an `if`, `done` for a `for`/`while` loop, or a missing closing quote `\"`.", "Bash, Linux", "bash shell syntax error unexpected eof closure"],
    ["/bin/bash^M: bad interpreter: No such file or directory", "Your script has Windows (CRLF) line endings instead of Unix (LF). Run `dos2unix script.sh` or fix your Git/editor line ending settings to use LF.", "Bash, Linux", "bash crlf dos2unix line endings bad interpreter"],

    # React Native / Expo
    ["Invariant Violation: View config getter callback for component 'X' must be a function", "You imported a React Native component incorrectly (e.g., a default import instead of named, or the component doesn't exist). Check your `import { View } from 'react-native'` syntax.", "React Native", "react native invariant violation view config import error"],
    ["Expo: Something went wrong. Unable to resolve module...", "The Metro bundler can't find a file. Often a typo in the import path. If the path is correct, clear the Expo cache: `expo start -c`.", "Expo, React Native", "expo react native metro resolve module cache"],

    # Next.js
    ["Next.js: Error: Text content does not match server-rendered HTML.", "Hydration error. You used something that differs on the server and client, like `new Date().getTime()`. Wrap client-side specific rendering in `useEffect` or check `mounted` state.", "Next.js", "nextjs react hydration mismatch text html date render"],
    ["Error: getStaticPaths is required for dynamic SSG pages", "You exported `getStaticProps` from a dynamic route (e.g., `[id].js`), but didn't export `getStaticPaths` to tell Next.js which IDs to pre-render. Add `getStaticPaths`.", "Next.js", "nextjs ssg getstaticpaths getstaticprops dynamic route"],

    # Python / Pip
    ["pip: Failed building wheel for X", "A C extension package couldn't compile. You need a C compiler and development headers. On Linux: `apt install build-essential python3-dev`. On Mac: `xcode-select --install`.", "Python, pip", "pip python wheel build error gcc compiler headers"],

    # Docker
    ["Docker: standard_init_linux.go:211: exec user process caused \"exec format error\"", "You built an image for an ARM architecture (like Apple M1) but are trying to run it on an x86 Linux machine, or vice versa. Build with `--platform linux/amd64`.", "Docker", "docker exec format error platform amd64 arm linux"],

    # C++
    ["error: expected constructor, destructor, or type conversion before '(' token", "Often caused by a missing `#include` for a type you're using, or a macro being expanded incorrectly. Check your includes.", "C++", "cpp c++ expected constructor destructor type compile"],

    # Java
    ["java.lang.IllegalArgumentException", "A method has been passed an illegal or inappropriate argument. Check the documentation for the method you called and ensure your arguments match the expected ranges/formats.", "Java", "java illegalargumentexception exception args invalid"],

    # Windows / CMD
    ["'X' is not recognized as an internal or external command, operable program or batch file.", "The program is not installed, or its directory is not in your system's PATH environment variable. Add the folder containing 'X' to your PATH and restart your terminal.", "Windows", "windows cmd path recognized external command operable batch"],

    # Misc
    ["CORS header ‘Access-Control-Allow-Origin’ missing", "The backend must whitelist your frontend's URL. If using Express, use the `cors` package. If using Nginx, add `add_header 'Access-Control-Allow-Origin' '*';`.", "HTTP, Browsers", "cors origin frontend backend missing allow header"],
    ["git: unable to access '...': SSL certificate problem", "Your local Git client doesn't trust the server's SSL cert. Update your CA certificates, or if it's an internal server you trust, bypass it with `git config http.sslVerify false`.", "Git", "git ssl certificate unable access trust local"],
    ["Error: ENOENT: no such file or directory, open '...'", "The file path is incorrect. Remember that relative paths in Node are resolved relative to the current working directory (`process.cwd()`), not the file location. Use `path.join(__dirname, 'file')`.", "Node.js", "node enoent file directory read path dirname open"],
    ["Vite: [plugin:vite:css] [postcss] require is not defined", "Your postcss.config.js is using CommonJS `require()` but your project is set to `\"type\": \"module\"`. Change `postcss.config.js` to `postcss.config.cjs` or use `import` syntax.", "Vite, PostCSS", "vite postcss require module cjs error plugin"],
    ["Python: NameError: name 'X' is not defined", "You used a variable before assigning it, misspelled it, or forgot to import the module that provides it. Check your spelling and imports.", "Python", "python nameerror undefined variable misspelled import"],
    ["Ruby: LoadError: cannot load such file -- X", "A `require` statement failed. Ensure the gem is in your Gemfile and `bundle install` was run, or the file path is correct.", "Ruby", "ruby loaderror require gem missing install"],
    ["React: Warning: Invalid DOM property `class`. Did you mean `className`?", "In React JSX, standard HTML attributes like `class` and `for` must be written as `className` and `htmlFor`.", "React", "react jsx dom class classname html property warning"],
    ["SQL: ERROR: column \"X\" must appear in the GROUP BY clause or be used in an aggregate function", "When using `GROUP BY`, any column in your `SELECT` must either be part of the `GROUP BY` list or wrapped in an aggregate function like `SUM()`, `MAX()`, or `COUNT()`.", "SQL", "sql group by aggregate function select error column"]
]

def append_bugs():
    import json
    import os
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'seed_bugs.json')
    
    with open(file_path, 'r') as f:
        existing = json.load(f)
        
    for err, fix, env, tags in NEW_BUGS:
        existing.append({
            "error": err,
            "fix": fix,
            "environment": env,
            "tags": tags,
            "confirmations": 2
        })
        
    with open(file_path, 'w') as f:
        json.dump(existing, f, indent=2)

if __name__ == '__main__':
    append_bugs()
    print(f"Added {len(NEW_BUGS)} bugs.")

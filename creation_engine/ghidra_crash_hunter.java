// Ghidra Script: Crash Vector Hunter for WoW.exe
// Extracts crash-prone functions, error strings, and exception handlers
// @category Analysis
// @author Kinetic Council

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.mem.*;
import ghidra.program.model.address.*;
import java.io.*;
import java.util.*;

public class ghidra_crash_hunter extends GhidraScript {

    @Override
    public void run() throws Exception {
        String outputPath = "C:\\Users\\thatg\\Desktop\\Modernize\\wow_analysis_report.txt";
        PrintWriter out = new PrintWriter(new FileWriter(outputPath));
        
        out.println("=== WoW.exe Crash Vector Analysis ===");
        out.println("Generated: " + new java.util.Date());
        out.println("Binary: " + currentProgram.getName());
        out.println("Architecture: " + currentProgram.getLanguage().getProcessor());
        out.println();

        // 1. Count total functions
        FunctionManager fm = currentProgram.getFunctionManager();
        int totalFunctions = 0;
        FunctionIterator allFuncs = fm.getFunctions(true);
        while (allFuncs.hasNext()) { allFuncs.next(); totalFunctions++; }
        out.println("Total Functions Found: " + totalFunctions);
        out.println();

        // 2. Find crash-related strings
        out.println("=== CRASH/ERROR STRINGS ===");
        Memory mem = currentProgram.getMemory();
        MemoryBlock[] blocks = mem.getBlocks();
        int errorStrings = 0;
        
        String[] crashPatterns = {
            "Error", "FATAL", "crash", "assert", "failed",
            "exception", "invalid", "corrupt", "overflow",
            "out of memory", "null pointer", "access violation",
            "stack overflow", "heap", "alloc", "leak"
        };
        
        // Search defined strings
        DataIterator dataIter = currentProgram.getListing().getDefinedData(true);
        while (dataIter.hasNext()) {
            Data data = dataIter.next();
            if (data.hasStringValue()) {
                String val = data.getDefaultValueRepresentation();
                for (String pattern : crashPatterns) {
                    if (val.toLowerCase().contains(pattern.toLowerCase())) {
                        out.println("  [" + data.getAddress() + "] " + val);
                        errorStrings++;
                        break;
                    }
                }
            }
        }
        out.println("Total error-related strings: " + errorStrings);
        out.println();

        // 3. Find functions that reference error/crash APIs
        out.println("=== CRITICAL API REFERENCES ===");
        String[] criticalAPIs = {
            "ExitProcess", "TerminateProcess", "RaiseException",
            "UnhandledExceptionFilter", "SetUnhandledExceptionFilter",
            "HeapAlloc", "HeapFree", "VirtualAlloc", "VirtualFree",
            "CreateThread", "CloseHandle"
        };
        
        SymbolTable st = currentProgram.getSymbolTable();
        for (String api : criticalAPIs) {
            SymbolIterator symbols = st.getSymbols(api);
            while (symbols.hasNext()) {
                Symbol sym = symbols.next();
                Reference[] refs = getReferencesTo(sym.getAddress());
                out.println("  " + api + " @ " + sym.getAddress() + " (referenced " + refs.length + " times)");
            }
        }
        out.println();

        // 4. Find large functions (complex = crash-prone)
        out.println("=== TOP 50 LARGEST FUNCTIONS (Complexity Hotspots) ===");
        List<String> largeFuncs = new ArrayList<>();
        FunctionIterator fi = fm.getFunctions(true);
        while (fi.hasNext()) {
            Function f = fi.next();
            long size = f.getBody().getNumAddresses();
            if (size > 500) {
                largeFuncs.add(String.format("  [%s] %s (%d bytes)", 
                    f.getEntryPoint(), f.getName(), size));
            }
        }
        Collections.sort(largeFuncs, (a, b) -> {
            int sizeA = Integer.parseInt(a.replaceAll(".*\\((\\d+) bytes\\)", "$1"));
            int sizeB = Integer.parseInt(b.replaceAll(".*\\((\\d+) bytes\\)", "$1"));
            return sizeB - sizeA;
        });
        for (int i = 0; i < Math.min(50, largeFuncs.size()); i++) {
            out.println(largeFuncs.get(i));
        }
        out.println();

        // 5. Find rendering-related functions (GxApi)
        out.println("=== RENDERING PIPELINE (GxApi) ===");
        fi = fm.getFunctions(true);
        while (fi.hasNext()) {
            Function f = fi.next();
            String name = f.getName();
            if (name.contains("Gx") || name.contains("render") || 
                name.contains("Draw") || name.contains("Shader") ||
                name.contains("Texture") || name.contains("Camera")) {
                out.println("  [" + f.getEntryPoint() + "] " + name + 
                    " (" + f.getBody().getNumAddresses() + " bytes)");
            }
        }
        out.println();

        // 6. Find network functions
        out.println("=== NETWORK LAYER ===");
        fi = fm.getFunctions(true);
        while (fi.hasNext()) {
            Function f = fi.next();
            String name = f.getName();
            if (name.contains("Net") || name.contains("Packet") || 
                name.contains("Socket") || name.contains("Send") ||
                name.contains("Recv") || name.contains("Connect")) {
                out.println("  [" + f.getEntryPoint() + "] " + name + 
                    " (" + f.getBody().getNumAddresses() + " bytes)");
            }
        }
        out.println();

        // 7. Find Lua/Script functions (addon system)
        out.println("=== LUA SCRIPTING ENGINE ===");
        fi = fm.getFunctions(true);
        while (fi.hasNext()) {
            Function f = fi.next();
            String name = f.getName();
            if (name.contains("lua") || name.contains("Lua") || 
                name.contains("Script") || name.contains("Addon")) {
                out.println("  [" + f.getEntryPoint() + "] " + name + 
                    " (" + f.getBody().getNumAddresses() + " bytes)");
            }
        }

        out.println();
        out.println("=== ANALYSIS COMPLETE ===");
        out.close();
        
        println("Crash Vector Report saved to: " + outputPath);
    }
}
